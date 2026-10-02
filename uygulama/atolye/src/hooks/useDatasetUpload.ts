import { useCallback, useState } from "react";

export type UploadStatus = "idle" | "uploading" | "synced" | "offline" | "error";

export interface UploadResult {
  id: number;
  name: string;
  filename: string;
  columns: string[];
  rowCount: number;
  sizeBytes: number;
}

export interface UploadOptions {
  name?: string;
  delimiter?: string;
  hasHeader?: boolean;
}

/**
 * P0: uploads the raw CSV to the server (S3/MinIO or local disk) and registers
 * dataset metadata in the database. Degrades gracefully: when the user is not
 * authenticated (401) the editor keeps working purely client-side ("offline").
 */
export function useDatasetUpload() {
  const [status, setStatus] = useState<UploadStatus>("idle");

  const upload = useCallback(
    async (file: File, opts?: UploadOptions): Promise<UploadResult | null> => {
      setStatus("uploading");
      try {
        const fd = new FormData();
        fd.append("file", file);
        if (opts?.name) fd.append("name", opts.name);
        if (opts?.delimiter) fd.append("delimiter", opts.delimiter);
        if (opts?.hasHeader !== undefined) fd.append("hasHeader", String(opts.hasHeader));

        const resp = await fetch("/api/datasets/upload", {
          method: "POST",
          body: fd,
          credentials: "include",
        });

        if (resp.status === 401) {
          setStatus("offline");
          return null;
        }
        if (!resp.ok) {
          setStatus("error");
          return null;
        }

        const data = (await resp.json()) as UploadResult;
        setStatus("synced");
        return data;
      } catch {
        setStatus("error");
        return null;
      }
    },
    [],
  );

  return { upload, status };
}
