import { useState, useEffect } from "react";
import Upload from "./components/Upload";
import { api } from "./api/client";

type Job = {
  id: number;
  status: "processing" | "completed";
  data?: any;
};

function App() {
  const [jobs, setJobs] = useState<Job[]>([]);

  // ✅ NEW: check if any job is processing
  const hasProcessing = jobs.some((job) => job.status === "processing");

  const resetAll = () => {
    setJobs([]);
  };

  const handleNewJob = (id: number) => {
    setJobs((prev) => [...prev, { id, status: "processing" }]);
  };

  useEffect(() => {
    // stop polling if no jobs are processing
    if (!jobs.some((job) => job.status === "processing")) {
      return;
    }

    const interval = setInterval(() => {
      jobs.forEach((job) => {
        if (job.status === "processing") {
          checkStatus(job.id);
        }
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [jobs]);

  const checkStatus = async (id: number) => {
    try {
      const res = await api.get(`/contracts/${id}/analysis`);
      const status = res.data.status;

      if (status === "completed") {
        setJobs((prev) =>
          prev.map((job) =>
            job.id === id
              ? { ...job, status: "completed", data: res.data }
              : job,
          ),
        );
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="container">
      <h1>📄 ContractGuard</h1>

      {jobs.length > 0 && (
        <>
          <button
            className="button"
            onClick={resetAll}
            disabled={hasProcessing} // ✅ disable when processing
            style={{
              marginBottom: 20,
              opacity: hasProcessing ? 0.5 : 1,
              cursor: hasProcessing ? "not-allowed" : "pointer",
            }}
          >
            Reset All
          </button>

          {hasProcessing && (
            <p style={{ color: "red", marginBottom: 10 }}>
              Cannot reset while processing is ongoing
            </p>
          )}
        </>
      )}

      <Upload onUploaded={handleNewJob} />

      {jobs.map((job) => (
        <div key={job.id} className="card">
          <h3>Contract #{job.id}</h3>

          {job.status === "processing" && <p>⏳ Processing...</p>}

          {job.status === "completed" && (
            <div>
              <h4>Risk Analysis</h4>

              {job.data.risks.map((r: any, i: number) => (
                <div
                  key={i}
                  style={{
                    border: "1px solid #eee",
                    borderRadius: 8,
                    padding: 12,
                    marginTop: 10,
                  }}
                >
                  <p>
                    <b>Type:</b> {r.risk_type}
                  </p>
                  <p>
                    <b>Severity:</b> {r.severity}
                  </p>
                  <p>
                    <b>Confidence:</b> {r.confidence.toFixed(2)}
                  </p>
                  <p>{r.explanation}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default App;
