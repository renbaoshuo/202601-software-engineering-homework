"use strict";

const MODEL = "XLabs-AI/flux-RealismLora";
const ROUTER = "https://router.huggingface.co/fal-ai";
const MAPPING_URL = `https://huggingface.co/api/models/${MODEL}?expand=inferenceProviderMapping`;
const TIMEOUT_MS = 180000;

const $ = (id) => document.getElementById(id);
let controller = null;
let record = null;
let imageBlob = null;
let imageObjectUrl = null;

function redact(value) {
  return String(value).replace(/hf_[a-zA-Z0-9]+/g, "[REDACTED]");
}

function log(message, details = {}) {
  const entry = { time: new Date().toISOString(), message: redact(message), ...details };
  record.events.push(entry);
  const row = document.createElement("li");
  const time = document.createElement("time");
  time.dateTime = entry.time;
  time.textContent = new Date(entry.time).toLocaleTimeString("zh-CN", { hour12: false });
  const text = document.createElement("span");
  text.textContent = entry.message;
  row.append(time, text);
  $("request-log").append(row);
  $("request-log").scrollTop = $("request-log").scrollHeight;
}

function setStatus(state, badge, message) {
  $("status-badge").dataset.state = state;
  $("status-badge").textContent = badge;
  $("status-message").dataset.state = state;
  $("status-message").textContent = message;
}

function syncPrompt() {
  $("prompt-count").textContent = `${$("prompt").value.length} 字符`;
}

function syncSettings() {
  document.querySelector(".settings summary span").textContent =
    `${$("image-size").value.replace("x", " × ")} · Seed ${$("seed").value || "随机"}`;
}

function resetImage() {
  $("result-image").hidden = true;
  $("result-image").removeAttribute("src");
  if (imageObjectUrl) URL.revokeObjectURL(imageObjectUrl);
  imageObjectUrl = null;
  imageBlob = null;
  $("download-image").disabled = true;
  $("image-meta").textContent = "等待本次图像";
  $("empty-state").hidden = false;
}

// 授权只发给 HF Router；模型元数据和图片下载均不携带 Token。
async function request(url, { token, body, signal, label }) {
  const headers = {};
  if (token) {
    if (!url.startsWith(`${ROUTER}/`)) throw new Error("拒绝向 HF Router 以外的地址发送 Token。");
    headers.Authorization = `Bearer ${token}`;
  }
  if (body) headers["Content-Type"] = "application/json";
  const method = body ? "POST" : "GET";
  const response = await fetch(url, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
    signal, credentials: "omit", referrerPolicy: "no-referrer", redirect: "error"
  });
  const requestId = response.headers.get("x-request-id") || response.headers.get("x-fal-request-id");
  log(`${label} · HTTP ${response.status}`, {
    method, url, status: response.status, requestId,
    contentType: response.headers.get("content-type")
  });
  if (!response.ok) {
    const text = redact(await response.text()).slice(0, 1200);
    const error = new Error(`${label}失败（HTTP ${response.status}）：${text || response.statusText}`);
    error.status = response.status;
    throw error;
  }
  return response;
}

async function jsonRequest(url, options) {
  const response = await request(url, options);
  try { return await response.json(); }
  catch (error) {
    if (options.signal.aborted) throw error;
    throw new Error(`${options.label}未返回有效 JSON。请导出记录并检查服务响应。`);
  }
}

function waitForPoll(signal) {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const abort = () => { clearTimeout(timer); reject(signal.reason); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, 2000);
    signal.addEventListener("abort", abort, { once: true });
  });
}

// 使用服务端返回的任务路径，保留 HF 路由和队列参数。
function queueUrl(rawUrl) {
  const url = new URL(rawUrl);
  let path;
  if (url.origin === "https://queue.fal.run") path = url.pathname;
  else if (url.origin === "https://router.huggingface.co" && url.pathname.startsWith("/fal-ai/")) {
    path = url.pathname.slice("/fal-ai".length);
  }
  if (!path?.startsWith("/fal-ai/") || !path.includes("/requests/")) {
    throw new Error("服务端返回了无法识别的任务地址。");
  }
  return `${ROUTER}${path}?_subdomain=queue`;
}

function errorHint(error) {
  const hints = {
    401: "请检查 Token 是否正确、是否过期或被撤销。",
    402: "推理额度不足。请到 Hugging Face 的 Billing 页面检查余额。",
    403: "请检查 Token 的 Inference Providers 权限，以及模型或账号的访问限制。",
    404: "模型或服务路径不可用。请查看模型主页的 Inference Providers。",
    422: "服务未接受请求参数。请查看错误正文及请求参数。",
    429: "请求频率或额度受限。请稍后手动重试。",
    500: "推理服务发生错误。请保留请求编号，稍后重试。",
    502: "推理服务暂时不可用。请稍后重试。",
    503: "推理服务忙或尚未就绪。请稍后重试。",
    504: "推理服务响应超时。请先检查 HF 使用记录，再决定是否重新生成。"
  };
  if (error instanceof TypeError) return "网络请求失败。请检查网络、浏览器跨域报错及 HF / fal.ai 服务状态。";
  return hints[error.status] || "请查看调用记录中的错误信息。";
}

$("generate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (controller) return;
  const token = $("api-key").value.trim();
  const prompt = $("prompt").value.trim();
  if (!/^hf_[a-zA-Z0-9]+$/.test(token)) {
    $("api-key").setCustomValidity("请输入以 hf_ 开头的 Hugging Face Token。");
    $("api-key").reportValidity();
    return;
  }
  if (!prompt) {
    $("prompt").setCustomValidity("请输入提示词，不能只包含空格。");
    $("prompt").reportValidity();
    return;
  }
  const [width, height] = $("image-size").value.split("x").map(Number);
  const parameters = {
    prompt, image_size: { width, height }, num_inference_steps: 28,
    guidance_scale: 3.5, num_images: 1, output_format: "png", enable_safety_checker: true
  };
  if ($("seed").value !== "") parameters.seed = Number($("seed").value);
  record = {
    startedAt: new Date().toISOString(), model: MODEL, baseModel: "black-forest-labs/FLUX.1-dev",
    provider: "fal-ai", outcome: "running", request: null, events: []
  };
  $("request-log").replaceChildren();
  $("request-body").textContent = "正在读取模型服务映射……";
  $("record-outcome").textContent = "正在请求";
  $("download-record").disabled = true;
  $("inputs").disabled = true;
  $("stop").hidden = false;
  $("viewfinder").setAttribute("aria-busy", "true");
  resetImage();
  $("empty-title").textContent = "正在构建这幅画面";
  $("empty-note").textContent = "请求与排队进度会显示在调用记录中";
  setStatus("loading", "正在连接", "正在检查模型的推理服务……");
  controller = new AbortController();
  const signal = controller.signal;
  const started = performance.now();
  let timedOut = false;
  const timer = setInterval(() => { $("elapsed").textContent = `${((performance.now() - started) / 1000).toFixed(1)} s`; }, 100);
  const deadline = setTimeout(() => { timedOut = true; controller.abort(); }, TIMEOUT_MS);
  try {
    log(`开始调用 ${MODEL}`);
    const metadata = await jsonRequest(MAPPING_URL, { signal, label: "读取模型映射" });
    const mapping = metadata.inferenceProviderMapping?.["fal-ai"];
    if (mapping?.status !== "live" || mapping.task !== "text-to-image" || mapping.adapter !== "lora" ||
        !/^fal-ai\/[a-zA-Z0-9/_-]+$/.test(mapping.providerId) || !mapping.adapterWeightsPath) {
      throw new Error("该模型当前没有可用的 fal.ai 文生图 LoRA 服务。请查看模型主页。");
    }
    parameters.loras = [{
      path: `https://huggingface.co/${MODEL}/resolve/main/${mapping.adapterWeightsPath.split("/").map(encodeURIComponent).join("/")}`,
      scale: 1
    }];
    const endpoint = `${ROUTER}/${mapping.providerId}?_subdomain=queue`;
    record.request = { endpoint, body: parameters };
    $("request-body").textContent = redact(JSON.stringify(record.request, null, 2));
    log(`服务 ${mapping.providerId} · 已指定 Realism LoRA`);
    setStatus("loading", "正在提交", "正在提交生成请求……");
    let task = await jsonRequest(endpoint, { token, body: parameters, signal, label: "提交生成请求" });
    if (!task.request_id || !task.response_url || !task.status_url) throw new Error("提交响应缺少任务编号或任务地址。");
    record.requestId = task.request_id;
    log(`请求编号 ${task.request_id}`);
    const resultUrl = queueUrl(task.response_url);
    const statusUrl = queueUrl(task.status_url);
    let previousState;
    while (true) {
      signal.throwIfAborted();
      if (task.error) throw new Error(`推理任务失败：${JSON.stringify(task.error)}`);
      if (!["IN_QUEUE", "IN_PROGRESS", "COMPLETED"].includes(task.status)) throw new Error(`无法识别的任务状态：${task.status}`);
      if (task.status !== previousState) {
        log(`任务状态 ${task.status}`);
        previousState = task.status;
      }
      if (task.status === "COMPLETED") break;
      const message = task.status === "IN_QUEUE"
        ? `正在排队${Number.isInteger(task.queue_position) ? `，前方 ${task.queue_position} 个请求` : ""}。`
        : "模型正在生成图像，请等待。";
      setStatus("loading", task.status === "IN_QUEUE" ? "排队中" : "生成中", message);
      await waitForPoll(signal);
      task = await jsonRequest(statusUrl, { token, signal, label: "查询任务" });
    }
    const result = await jsonRequest(resultUrl, { token, signal, label: "获取生成结果" });
    record.response = result;
    if (result.has_nsfw_concepts?.[0]) throw new Error("本次图像被服务端内容检查拦截，请修改提示词。");
    const image = result.images?.[0];
    if (!image?.url || new URL(image.url).protocol !== "https:") throw new Error("服务未返回可用的 HTTPS 图像地址。");
    setStatus("loading", "读取图像", "生成已完成，正在下载图像……");
    const response = await request(image.url, { signal, label: "下载图像" });
    const blob = await response.blob();
    if (!/^image\/(png|jpeg|webp)(;|$)/i.test(blob.type) || !blob.size) throw new Error("返回内容不是有效的 PNG、JPEG 或 WebP 图像。");
    imageObjectUrl = URL.createObjectURL(blob);
    $("result-image").src = imageObjectUrl;
    await $("result-image").decode();
    signal.throwIfAborted();
    imageBlob = blob;
    $("empty-state").hidden = true;
    $("result-image").hidden = false;
    $("download-image").disabled = false;
    record.image = { type: blob.type, bytes: blob.size, width: $("result-image").naturalWidth, height: $("result-image").naturalHeight };
    record.outcome = "success";
    $("image-meta").textContent = `${record.image.width} × ${record.image.height} · ${(blob.size / 1024).toFixed(0)} KB · Seed ${result.seed ?? parameters.seed ?? "未返回"}`;
    log(`图像解码成功 · ${record.image.width} × ${record.image.height} · ${blob.type}`);
    setStatus("success", "生成成功", `图像已生成。请下载图像、导出调用记录，并截图保存本页。`);
  } catch (error) {
    const aborted = signal.aborted;
    record.outcome = timedOut ? "timeout" : aborted ? "stopped" : "error";
    const message = aborted
      ? `${timedOut ? "等待已超过 180 秒" : "已停止等待"}。远端任务可能仍在运行或计费，请检查 HF 使用记录。`
      : `${errorHint(error)} ${redact(error.message || String(error))}`;
    record.error = message;
    log(message);
    resetImage();
    $("empty-title").textContent = aborted ? "本次等待已结束" : "这次没有取得图像";
    $("empty-note").textContent = "查看下方提示和调用记录后再试";
    setStatus("error", aborted ? "等待结束" : "调用失败", message);
  } finally {
    clearInterval(timer);
    clearTimeout(deadline);
    record.finishedAt = new Date().toISOString();
    record.durationSeconds = Number(((performance.now() - started) / 1000).toFixed(2));
    $("elapsed").textContent = `${record.durationSeconds} s`;
    $("record-outcome").textContent = `${record.outcome.toUpperCase()} · ${new Date(record.startedAt).toLocaleString("zh-CN", { hour12: false })}`;
    $("inputs").disabled = false;
    $("stop").hidden = true;
    $("viewfinder").setAttribute("aria-busy", "false");
    $("download-record").disabled = false;
    controller = null;
  }
});

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

function filename(suffix) {
  return `flux-${record.startedAt.replace(/[:.]/g, "-")}${suffix}`;
}

$("download-image").addEventListener("click", () => {
  if (!imageBlob) return;
  const extension = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp" }[imageBlob.type.split(";")[0].toLowerCase()];
  download(imageBlob, filename(`.${extension}`));
});
$("download-record").addEventListener("click", () => {
  if (record && !controller) download(new Blob([redact(JSON.stringify(record, null, 2))], { type: "application/json" }), filename("-record.json"));
});
$("stop").addEventListener("click", () => controller?.abort());
$("clear-key").addEventListener("click", () => { $("api-key").value = ""; $("api-key").setCustomValidity(""); $("api-key").focus(); });
$("api-key").addEventListener("input", () => $("api-key").setCustomValidity(""));
$("prompt").addEventListener("input", () => { $("prompt").setCustomValidity(""); syncPrompt(); });
$("image-size").addEventListener("change", syncSettings);
$("seed").addEventListener("input", syncSettings);
syncPrompt();
syncSettings();
