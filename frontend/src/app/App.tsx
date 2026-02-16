import { useState, useRef, useMemo } from 'react';
import { QueryPanel } from './components/QueryPanel';
import type { QuerySubmitPayload } from './components/QueryPanel';
import { AnswerDisplay } from './components/AnswerDisplay';
import { ExplainabilityPanel } from './components/ExplainabilityPanel';
import { Activity, Brain } from 'lucide-react';

export type ViewMode = 'user' | 'research';

export interface Answer {
  llmOnly: string;
  kgLlm: string;
  entities: string[];
  snomedConcepts: Array<{ concept: string; code: string }>;
  subgraphSummary: string;
  reasoningPath: string[];
}

interface KgResponse {
  extracted_terms?: string[];
  debug?: Array<Record<string, unknown>>;
  mapped_to?: {
    bank_id?: string | null;
    qtype?: string | null;
    question?: string | null;
  };
  results?: Array<{
    answer?: string;
    subgraph_summary?: string[];
    note?: string;
  }>;
}

interface LlmOnlyResponse {
  results?: Array<{
    answer?: string;
  }>;
}

declare global {
  interface Window {
    __CONFIG__?: {
      API_BASE_URL?: string;
      API_KEY?: string;
    };
  }
}

function readConfig() {
  const cfg = window.__CONFIG__ || {};
  return {
    apiBaseUrl: (cfg.API_BASE_URL || window.location.origin).replace(/\/+$/, ''),
    apiKey: (cfg.API_KEY || '').trim(),
  };
}

function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('user');
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [showExplainability, setShowExplainability] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);
  const config = useMemo(readConfig, []);

  const handleSubmitQuery = async ({ queryText, queryType, topicKey }: QuerySubmitPayload) => {
    setQuery(queryText);
    setIsLoading(true);
    setAnswer(null);

    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);

    try {
      const headers: Record<string, string> = {};
      if (config.apiKey) {
        headers['X-API-KEY'] = config.apiKey;
      }

      const kgUrl = new URL('/demo/search', `${config.apiBaseUrl}/`);
      kgUrl.searchParams.set('question', queryText);
      kgUrl.searchParams.set('mode', viewMode);
      if (topicKey) {
        kgUrl.searchParams.set('topic_key', topicKey);
      }
      if (queryType !== 'free') {
        kgUrl.searchParams.set('qtype', queryType);
      }
      const llmUrl = new URL('/llm_only', `${config.apiBaseUrl}/`);
      llmUrl.searchParams.set('question', queryText);

      const [kgResp, llmResp] = await Promise.all([
        fetch(kgUrl.toString(), { headers }),
        fetch(llmUrl.toString(), { headers }),
      ]);

      const kgData: KgResponse = await kgResp.json();
      const llmData: LlmOnlyResponse = await llmResp.json();

      if (!kgResp.ok) {
        throw new Error(`KG request failed (${kgResp.status})`);
      }
      if (!llmResp.ok) {
        throw new Error(`LLM request failed (${llmResp.status})`);
      }

      const mappedCode = kgData.mapped_to?.bank_id || '-';
      const mappedFacet = kgData.mapped_to?.qtype || '-';
      const resultConcept = (kgData.results?.[0] as Record<string, unknown> | undefined)?.conceptId as string | undefined;
      const fallback = (kgData.results?.[0]?.note as string | undefined) ||
        (kgData.debug || []).find((d) => typeof d.fallback === 'string')?.fallback as string | undefined;

      const reasoningPath = [
        `1. 問題解析：${queryText}`,
        `2. 類型判定：${mappedFacet}`,
        `3. 概念映射：${mappedCode}`,
        `4. 子圖檢索：${(kgData.results?.[0]?.subgraph_summary || []).length} 條摘要`,
        fallback ? `5. Fallback：${fallback}` : '5. Fallback：無',
        '6. 生成答案：知識圖譜 + LLM 與純 LLM 比較',
      ];

      const uiAnswer: Answer = {
        llmOnly: llmData.results?.[0]?.answer || '無資料',
        kgLlm: kgData.results?.[0]?.answer || '無資料',
        entities: kgData.extracted_terms || [],
        snomedConcepts: [
          { concept: 'Mapped Concept', code: String(mappedCode !== '-' ? mappedCode : resultConcept || '-') },
          { concept: 'Facet', code: String(mappedFacet) },
        ],
        subgraphSummary: (kgData.results?.[0]?.subgraph_summary || []).join('；') || '無子圖摘要',
        reasoningPath,
      };

      setAnswer(uiAnswer);
      setShowExplainability(viewMode === 'research');
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤';
      const failedAnswer: Answer = {
        llmOnly: `系統請求失敗：${message}`,
        kgLlm: `系統請求失敗：${message}`,
        entities: [],
        snomedConcepts: [],
        subgraphSummary: '請確認後端 API、Neo4j、Ollama 是否已啟動。',
        reasoningPath: ['1. 前端發送 API 請求', '2. 連線失敗，請檢查服務狀態'],
      };
      setAnswer(failedAnswer);
      setShowExplainability(viewMode === 'research');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-cyan-50/30 to-teal-50/20">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">醫療知識問答系統</h1>
                <p className="text-xs text-slate-500">基於大型語言模型與醫學知識圖譜</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('user')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                    viewMode === 'user' ? 'bg-white text-cyan-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    <span>使用者模式</span>
                  </div>
                </button>
                <button
                  onClick={() => {
                    setViewMode('research');
                    if (answer) setShowExplainability(true);
                  }}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                    viewMode === 'research' ? 'bg-white text-cyan-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4" />
                    <span>研究模式</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          <QueryPanel onSubmit={handleSubmitQuery} isLoading={isLoading} disabled={isLoading} />

          <div ref={resultsRef}>
            {(answer || isLoading) && (
              <AnswerDisplay answer={answer} isLoading={isLoading} viewMode={viewMode} query={query} />
            )}
          </div>

          {answer && viewMode === 'research' && (
            <ExplainabilityPanel
              answer={answer}
              isOpen={showExplainability}
              onToggle={() => setShowExplainability(!showExplainability)}
            />
          )}
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white/50 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-slate-600">
            <p>此系統僅供研究與演示用途，不應作為專業醫療建議替代。</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
