"use strict";
const el = (id) => document.getElementById(id);
let token = "",
  epoch = 0,
  timer = null,
  controller = null,
  busy = false,
  paused = false;
let frameURL = null,
  frameMeta = null,
  capturedAt = 0,
  frameBlob = null;
const controls = ["refresh", "pause", "save", "apply-crop"];
function error(message = "") {
  el("error").textContent = message;
  el("error").hidden = !message;
}
function revokeFrame() {
  if (frameURL) URL.revokeObjectURL(frameURL);
  frameURL = null;
  frameBlob = null;
  frameMeta = null;
  capturedAt = 0;
  el("frame").removeAttribute("src");
  el("frame").hidden = true;
  el("empty").hidden = false;
  el("save").disabled = true;
  el("frame-info").textContent = "No frame captured";
}
function cancel() {
  epoch++;
  clearTimeout(timer);
  controller?.abort();
  controller = null;
  busy = false;
}
function state(message) {
  el("frame-state").textContent = message;
}
function disconnect(message = "") {
  cancel();
  token = "";
  paused = false;
  revokeFrame();
  el("token").value = "";
  el("connect-form").hidden = false;
  el("session").hidden = true;
  el("connection").textContent = "Disconnected";
  el("connection").classList.remove("live");
  el("monitor").disabled = true;
  controls.forEach((id) => (el(id).disabled = true));
  el("demo-banner").hidden = true;
  state("Ready when you are");
  el("pause").textContent = "Pause";
  error(message);
}
async function request(path, signal) {
  const response = await fetch(path, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    credentials: "omit",
    redirect: "error",
    signal,
  });
  if (response.status === 401) {
    disconnect(
      "Access token rejected. Reconnect with the host’s current token.",
    );
    throw new Error("Authentication required");
  }
  if (!response.ok) {
    let message = `Host returned HTTP ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {}
    throw new Error(message);
  }
  return response;
}
function zoom() {
  el("stage").classList.toggle("fit", el("zoom").value === "fit");
  el("frame").style.width =
    frameMeta && el("zoom").value !== "fit"
      ? `${frameMeta.width * Number(el("zoom").value)}px`
      : "";
}
function schedule() {
  clearTimeout(timer);
  const seconds = Number(el("interval").value);
  if (token && !paused && !document.hidden && seconds > 0)
    timer = setTimeout(capture, seconds * 1000);
}
async function capture() {
  if (!token || busy || document.hidden) return;
  busy = true;
  const version = epoch;
  const abort = new AbortController();
  controller = abort;
  const timeout = setTimeout(() => abort.abort(), 20000);
  state("Capturing…");
  try {
    const params = new URLSearchParams({
      monitor: el("monitor").value,
      max_width: el("resolution").value,
      quality: el("quality").value,
    });
    for (const k of ["x", "y", "width", "height"])
      params.set(k, el(`crop-${k}`).value);
    const response = await request(`/api/frame?${params}`, abort.signal);
    const blob = await response.blob(),
      meta = JSON.parse(response.headers.get("X-Beacn-Frame"));
    const url = URL.createObjectURL(blob),
      probe = new Image();
    probe.src = url;
    try {
      await probe.decode();
    } catch (err) {
      URL.revokeObjectURL(url);
      throw err;
    }
    if (version !== epoch || !token) {
      URL.revokeObjectURL(url);
      return;
    }
    if (frameURL) URL.revokeObjectURL(frameURL);
    frameURL = url;
    frameBlob = blob;
    frameMeta = meta;
    capturedAt = Date.parse(meta.captured_at);
    el("frame").src = url;
    el("frame").hidden = false;
    el("frame").classList.remove("stale");
    el("empty").hidden = true;
    el("save").disabled = false;
    el("frame-info").textContent =
      `${meta.width} × ${meta.height} · ${Math.round(blob.size / 1024)} KB`;
    el("demo-banner").hidden = !meta.demo;
    zoom();
    error();
    state(
      paused
        ? "Paused · last frame retained"
        : Number(el("interval").value) === 0
          ? "Manual capture"
          : "Receiving frames",
    );
  } catch (err) {
    if (version === epoch && token) {
      error(
        err.name === "AbortError"
          ? "Capture timed out. Check the host connection."
          : err.message,
      );
      state("No fresh frame");
      el("frame").classList.add("stale");
    }
  } finally {
    clearTimeout(timeout);
    if (version === epoch) {
      busy = false;
      controller = null;
      schedule();
    }
  }
}
el("connect-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  cancel();
  const version = epoch;
  token = el("token").value.trim();
  el("token").value = "";
  el("connect").disabled = true;
  error();
  const abort = new AbortController();
  controller = abort;
  const timeout = setTimeout(() => abort.abort(), 15000);
  try {
    const status = await (await request("/api/status", abort.signal)).json();
    const data = await (await request("/api/monitors", abort.signal)).json();
    if (version !== epoch) return;
    if (!data.monitors.length)
      throw new Error("No displays available in this host session.");
    el("monitor").replaceChildren(
      ...data.monitors.map((m) => {
        const option = document.createElement("option");
        option.value = m.id;
        option.textContent = `Display ${m.id} · ${m.width} × ${m.height}`;
        return option;
      }),
    );
    el("monitor").disabled = false;
    el("connect-form").hidden = true;
    el("session").hidden = false;
    el("connection").textContent = status.demo ? "Demo connected" : "Connected";
    el("connection").classList.add("live");
    controls
      .filter((id) => id !== "save")
      .forEach((id) => (el(id).disabled = false));
    el("demo-banner").hidden = !status.demo;
    controller = null;
    await capture();
  } catch (err) {
    if (version === epoch)
      disconnect(
        err.name === "AbortError"
          ? "Connection timed out. Check the host address."
          : err.message,
      );
  } finally {
    clearTimeout(timeout);
    el("connect").disabled = false;
  }
});
el("disconnect").addEventListener("click", () => disconnect());
el("refresh").addEventListener("click", capture);
el("pause").addEventListener("click", () => {
  paused = !paused;
  cancel();
  el("pause").textContent = paused ? "Resume" : "Pause";
  state(paused ? "Paused · last frame retained" : "Ready to capture");
  if (!paused) capture();
});
el("interval").addEventListener("change", () => {
  schedule();
  if (token)
    state(
      paused
        ? "Paused · last frame retained"
        : el("interval").value === "0"
          ? "Manual capture"
          : "Receiving frames",
    );
});
function refreshSettings(clear = false) {
  cancel();
  if (clear) revokeFrame();
  if (token) capture();
}
el("monitor").addEventListener("change", () => {
  for (const k of ["x", "y", "width", "height"]) el(`crop-${k}`).value = 0;
  refreshSettings(true);
});
el("resolution").addEventListener("change", () => refreshSettings());
el("quality").addEventListener("change", () => refreshSettings());
el("apply-crop").addEventListener("click", () => refreshSettings(true));
el("zoom").addEventListener("change", zoom);
el("fullscreen").disabled = !document.fullscreenEnabled;
el("fullscreen").addEventListener("click", () =>
  el("stage")
    .requestFullscreen()
    .catch(() => error("Full screen is unavailable in this browser.")),
);
el("save").addEventListener("click", () => {
  if (!frameBlob) return;
  const a = document.createElement("a");
  a.href = frameURL;
  a.download = `beacn-view-${frameMeta.frame_id}.jpg`;
  a.click();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    cancel();
    if (token) state("Tab hidden · capture paused");
  } else if (token && !paused) capture();
});
window.addEventListener("pagehide", () => disconnect());
setInterval(() => {
  if (capturedAt) {
    const age = Math.max(0, Math.floor((Date.now() - capturedAt) / 1000));
    el("freshness").textContent =
      `Last capture ${age}s ago${paused ? " · paused" : ""}. Save JPEG creates a local file.`;
    if (age > Math.max(5, Number(el("interval").value) * 2))
      el("frame").classList.add("stale");
  } else
    el("freshness").textContent = "Frames stay in memory unless you save one.";
}, 1000);
zoom();

if (matchMedia("(max-width:650px)").matches) el("settings").open = false;
