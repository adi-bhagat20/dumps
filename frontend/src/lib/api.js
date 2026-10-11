const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function ensureServerAwake(onStatus) {
  // Check if server is already awake
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: 'no-store' });
    if (res.ok) return true;
  } catch (e) {
    // server is likely sleeping
  }

  onStatus?.("Waking up cloud server (takes ~30-40s on free tier)...");

  // Poll /api/health every 3.5 seconds for up to 60s
  const start = Date.now();
  while (Date.now() - start < 60000) {
    await new Promise((r) => setTimeout(r, 3500));
    try {
      const res = await fetch(`${API_BASE}/api/health`, { cache: 'no-store' });
      if (res.ok) {
        onStatus?.("Server ready! Starting upload...");
        return true;
      }
    } catch (e) {
      // still spinning up
    }
  }
  throw new Error("Server took too long to wake up. Please click Try Again.");
}

export async function uploadFolder(files, folderName = "Photos") {
  const formData = new FormData();
  formData.append("folder_name", folderName);
  
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  const response = await fetch(`${API_BASE}/api/uploads`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Upload failed");
  }

  return await response.json();
}

export async function startJob(uploadId) {
  const response = await fetch(`${API_BASE}/api/jobs/${uploadId}/start`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to start job" }));
    throw new Error(error.detail || "Failed to start job");
  }

  return await response.json();
}

export async function getClusters(jobId) {
  const response = await fetch(`${API_BASE}/api/clusters/${jobId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch clusters");
  }
  const data = await response.json();
  // Adjust thumbnail URLs if API_BASE is set
  if (data.clusters) {
    data.clusters = data.clusters.map(c => ({
      ...c,
      thumbnail_url: c.thumbnail_url ? (c.thumbnail_url.startsWith('http') ? c.thumbnail_url : `${API_BASE}${c.thumbnail_url}`) : null
    }));
  }
  return data;
}

export async function getClusterPhotos(jobId, clusterId) {
  const response = await fetch(`${API_BASE}/api/clusters/${jobId}/${clusterId}/photos`);
  if (!response.ok) {
    throw new Error("Failed to fetch photos for cluster");
  }
  const data = await response.json();
  if (data.photos) {
    data.photos = data.photos.map(p => ({
      ...p,
      url: p.url.startsWith('http') ? p.url : `${API_BASE}${p.url}`
    }));
  }
  return data;
}

export function getClusterZipUrl(jobId, clusterId) {
  return `${API_BASE}/api/clusters/${jobId}/${clusterId}/zip`;
}
