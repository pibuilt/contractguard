import { useState } from "react";
import Upload from "./components/Upload";
import Status from "./components/Status";
import Results from "./components/Results";

function App() {
  const [contractId, setContractId] = useState<number | null>(null);
  const [data, setData] = useState<any>(null);

  return (
    <div>
      <h1>ContractGuard</h1>

      {!contractId && <Upload onUploaded={setContractId} />}

      {contractId && !data && (
        <Status contractId={contractId} onComplete={setData} />
      )}

      {data && <Results data={data} />}
    </div>
  );
}

export default App;
