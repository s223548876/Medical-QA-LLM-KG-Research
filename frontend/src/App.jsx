import { useMemo, useState } from "react";

const TOPICS = [
  { display: "氣喘（Asthma）", key: "Asthma" },
  { display: "糖尿病（Diabetes）", key: "Diabetes" },
  { display: "心臟病（Heart disease）", key: "Heart disease" },
  { display: "高血壓（Hypertension）", key: "Hypertension" },
  { display: "流感（Influenza）", key: "Influenza" },
  { display: "結核病（Tuberculosis）", key: "Tuberculosis" },
  { display: "癌症（Cancer）", key: "Cancer" },
  { display: "中風（Stroke）", key: "Stroke" },
  { display: "阿茲海默症（Alzheimer's disease）", key: "Alzheimer's disease" },
  { display: "帕金森氏症（Parkinson's disease）", key: "Parkinson's disease" },
  { display: "慢性腎臟病（Chronic kidney disease）", key: "Chronic kidney disease" },
  { display: "骨質疏鬆（Osteoporosis）", key: "Osteoporosis" },
  { display: "憂鬱症（Depression）", key: "Depression" },
  { display: "焦慮疾患（Anxiety disorders）", key: "Anxiety disorders" },
  { display: "肥胖（Obesity）", key: "Obesity" },
  { display: "肺炎（Pneumonia）", key: "Pneumonia" },
  { display: "肝炎（Hepatitis）", key: "Hepatitis" },
  { display: "HIV／愛滋病（HIV/AIDS）", key: "HIV/AIDS" },
  { display: "新冠肺炎（COVID-19）", key: "COVID-19" },
  { display: "過敏（Allergies）", key: "Allergies" },
  { display: "關節炎（Arthritis）", key: "Arthritis" },
  { display: "偏頭痛（Migraine）", key: "Migraine" },
  { display: "癲癇（Epilepsy）", key: "Epilepsy" },
  { display: "貧血（Anemia）", key: "Anemia" },
  { display: "甲狀腺疾病（Thyroid disorders）", key: "Thyroid disorders" },
  { display: "皮膚癌（Skin cancer）", key: "Skin cancer" },
  { display: "乳癌（Breast cancer）", key: "Breast cancer" },
  { display: "子宮頸癌（Cervical cancer）", key: "Cervical cancer" },
  { display: "白血病（Leukemia）", key: "Leukemia" },
  { display: "睡眠呼吸中止症（Sleep apnea）", key: "Sleep apnea" },
  { display: "胃食道逆流（GERD）", key: "GERD" },
  { display: "腸躁症（Irritable bowel syndrome）", key: "Irritable bowel syndrome" },
  { display: "乳糜瀉（Celiac disease）", key: "Celiac disease" },
  { display: "瘧疾（Malaria）", key: "Malaria" },
  { display: "慢性阻塞性肺病（Chronic obstructive pulmonary disease）", key: "Chronic obstructive pulmonary disease" },
];

const QUESTION_TEMPLATES = [
  { qtype: "definition", make: (topicDisplay) => `什麼是${topicDisplay}？` },
  { qtype: "symptoms", make: (topicDisplay) => `${topicDisplay}有哪些症狀？` },
  { qtype: "treatments", make: (topicDisplay) => `${topicDisplay}要怎麼治療？` },
];

const SURVEY_URL = "https://forms.gle/d3x6AFRZjCVHX2gu6";

function readConfig() {
  const cfg = window.__CONFIG__ || {};
  return {
    apiBaseUrl: (cfg.API_BASE_URL || window.location.origin).replace(/\/+$/, ""),
    apiKey: (cfg.API_KEY || "").trim(),
  };
}

export default function App() {
  const config = useMemo(readConfig, []);
  const [mode, setMode] = useState("research");
  const [question, setQuestion] = useState("");
  const [selectedTopicKey, setSelectedTopicKey] = useState("");
  const [selectedQtype, setSelectedQtype] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSelectTemplate = (topic, template) => {
    setSelectedTopicKey(topic.key);
    setSelectedQtype(template.qtype);
    setQuestion(template.make(topic.display));
  };

  const handleAsk = async () => {
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setStatus("正在尋找最相近的問題...");

    try {
      const url = new URL("/demo/search", `${config.apiBaseUrl}/`);
      url.searchParams.set("question", trimmed);
      if (selectedTopicKey) {
        url.searchParams.set("topic_key", selectedTopicKey);
      }
      if (selectedQtype) {
        url.searchParams.set("qtype", selectedQtype);
      }

      const headers = {};
      if (config.apiKey) {
        headers["X-API-KEY"] = config.apiKey;
      }

      const response = await fetch(url.toString(), { headers });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `Request failed (${response.status})`);
      }

      if (!data.matched) {
        setStatus(`${data.message || "Not matched"} (similarity=${data.similarity ?? "n/a"})`);
        return;
      }

      setStatus(`已配對（相似度：${data.similarity}）`);
      setResult(data);
    } catch (err) {
      setStatus("");
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const answers = result?.answers || {};
  const mapped = result?.mapped_to || {};
  const debug = result?.debug || [];
  const subgraphSummary = (result?.results && result.results[0]?.subgraph_summary) || [];

  return (
    <main className="page">
      <section className="hero card">
        <h1>Medical QA Research</h1>
        <p className="small">
          僅供研究評估之用，不構成醫療建議。此示範會將您的輸入與題庫中最接近的問題進行比對。
          您可以詢問疾病定義、症狀、治療方式。
        </p>

        <div className="mode-toggle" role="group" aria-label="Mode Toggle">
          <button
            className={mode === "research" ? "active" : ""}
            type="button"
            onClick={() => setMode("research")}
          >
            Research mode
          </button>
          <button
            className={mode === "user" ? "active" : ""}
            type="button"
            onClick={() => setMode("user")}
          >
            User mode
          </button>
        </div>

        <details open>
          <summary>可詢問的 35 個 Topics（點一下自動帶入範例問題）</summary>
          <p className="small topic-help">
            建議先點選一個 topic，再修改成你想問的中文句子（例如：什麼是___ / 有哪些症狀 / 要怎麼治療）。
          </p>
          <table className="topic-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>可點選範例（會自動填入輸入框）</th>
              </tr>
            </thead>
            <tbody>
              {TOPICS.map((topic) => (
                <tr key={topic.key}>
                  <td>{topic.display}</td>
                  <td>
                    {QUESTION_TEMPLATES.map((template) => {
                      const text = template.make(topic.display);
                      return (
                        <button
                          key={`${topic.key}-${template.qtype}`}
                          type="button"
                          className="topic-pill"
                          onClick={() => handleSelectTemplate(topic, template)}
                          title={text}
                        >
                          {text}
                        </button>
                      );
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>

        <label htmlFor="questionInput" className="field-label">請輸入問題:</label>
        <textarea
          id="questionInput"
          placeholder="e.g. 什麼是高血壓?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div className="actions">
          <button type="button" onClick={handleAsk} disabled={loading}>送出</button>
          <button type="button" onClick={() => window.open(SURVEY_URL, "_blank")}>打開問卷</button>
        </div>

        {loading && <div className="loading">Loading...</div>}
        {status && <div className="status">{status}</div>}
        {error && <div className="error">{error}</div>}
      </section>

      {result && (
        <section className="panels">
          <article className="card panel">
            <h2>Explain Panel</h2>
            <p className="small">
              Mapped to: [{mapped.bank_id}] ({mapped.qtype}) {mapped.question}
            </p>
            <div className="explain-block">
              <h3>Debug</h3>
              <pre>{JSON.stringify(debug, null, 2)}</pre>
            </div>
            <div className="explain-block">
              <h3>Subgraph Summary</h3>
              {subgraphSummary.length ? (
                <ul>
                  {subgraphSummary.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : (
                <p className="small">No subgraph summary returned.</p>
              )}
            </div>
          </article>

          <article className="card panel">
            <h2>Answer Panel</h2>
            {mode === "research" ? (
              <div className="answer-grid">
                <div className="answer-box">
                  <h3>{answers.a_label || "Answer A"}</h3>
                  <pre>{answers.a_text || ""}</pre>
                </div>
                <div className="answer-box">
                  <h3>{answers.b_label || "Answer B"}</h3>
                  <pre>{answers.b_text || ""}</pre>
                </div>
              </div>
            ) : (
              <div className="answer-box">
                <h3>Answer</h3>
                <pre>{answers.a_text || answers.b_text || ""}</pre>
              </div>
            )}
          </article>
        </section>
      )}
    </main>
  );
}
