import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function Status({ contractId, onComplete }: any) {
  const [status, setStatus] = useState("pending");

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/contracts/${contractId}/analysis`);

        const currentStatus = res.data.status;
        setStatus(currentStatus);

        if (currentStatus === "completed") {
          clearInterval(interval);
          onComplete(res.data);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [contractId]);

  return <div>Status: {status}</div>;
}
