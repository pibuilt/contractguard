import { useState } from "react";
import { api } from "../api/client";

export default function Upload({ onUploaded }: any) {
  const [files, setFiles] = useState<File[]>([]);

  const handleUpload = async () => {
    if (files.length === 0) return alert("Select files");

    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      const res = await api.post("/contracts", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const contractId = res.data.data.contract_id;

      onUploaded(contractId); // send each job up
    }

    setFiles([]); // clear selection
  };

  return (
    <div className="card">
      <h2>Upload Contracts</h2>

      <input
        className="input"
        type="file"
        multiple
        onChange={(e) => setFiles(Array.from(e.target.files || []))}
      />

      <br />

      <button className="button" onClick={handleUpload}>
        Upload
      </button>
    </div>
  );
}
