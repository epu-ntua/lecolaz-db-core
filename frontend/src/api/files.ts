const API_BASE = "http://localhost:8000";

export async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function listFiles() {
  const res = await fetch(`${API_BASE}/files`); // or `/files` if you switch later
  if (!res.ok) throw new Error("List failed");
  return res.json();
}
