export async function uploadFolder(files, folderName = "Photos") {
  const formData = new FormData();
  formData.append("folder_name", folderName);
  
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  const response = await fetch("/api/uploads", {
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
  const response = await fetch(`/api/jobs/${uploadId}/start`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to start job" }));
    throw new Error(error.detail || "Failed to start job");
  }

  return await response.json();
}

export async function getClusters(jobId) {
  const response = await fetch(`/api/clusters/${jobId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch clusters");
  }
  return await response.json();
}

export async function getClusterPhotos(jobId, clusterId) {
  const response = await fetch(`/api/clusters/${jobId}/${clusterId}/photos`);
  if (!response.ok) {
    throw new Error("Failed to fetch photos for cluster");
  }
  return await response.json();
}

export function getClusterZipUrl(jobId, clusterId) {
  return `/api/clusters/${jobId}/${clusterId}/zip`;
}
