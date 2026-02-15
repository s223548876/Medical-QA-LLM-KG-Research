import { useState } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { TopicSuggestions } from './TopicSuggestions';
import { Loader2, Send, Sparkles, MessageSquare, BookOpen, Activity, Pill } from 'lucide-react';

export type QueryType = 'free' | 'definition' | 'symptoms' | 'treatments';

export interface QuerySubmitPayload {
  queryText: string;
  queryType: QueryType;
  topicKey?: string;
}

interface QueryPanelProps {
  onSubmit: (payload: QuerySubmitPayload) => void;
  isLoading: boolean;
  disabled: boolean;
}

export function QueryPanel({ onSubmit, isLoading, disabled }: QueryPanelProps) {
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState<QueryType>('free');
  const [topicKey, setTopicKey] = useState<string>('');

  const queryTypes = [
    { type: 'free' as QueryType, label: '自由詢問', icon: MessageSquare, prefix: '' },
    { type: 'definition' as QueryType, label: '定義', icon: BookOpen, prefix: '請說明' },
    { type: 'symptoms' as QueryType, label: '症狀', icon: Activity, prefix: '請列出' },
    { type: 'treatments' as QueryType, label: '治療', icon: Pill, prefix: '請介紹' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !disabled) {
      let finalQuery = query.trim();

      if (topicKey) {
        if (queryType === 'definition') finalQuery = `什麼是${query.trim()}？`;
        else if (queryType === 'symptoms') finalQuery = `${query.trim()}有哪些症狀？`;
        else if (queryType === 'treatments') finalQuery = `${query.trim()}要怎麼治療？`;
      }

      onSubmit({
        queryText: finalQuery,
        queryType,
        topicKey: topicKey || undefined,
      });
    }
  };

  const TOPIC_KEY_MAP: Record<string, string> = {
    '氣喘': 'Asthma',
    '糖尿病': 'Diabetes',
    '心臟病': 'Heart disease',
    '高血壓': 'Hypertension',
    '流行性感冒': 'Influenza',
    '結核病': 'Tuberculosis',
    '肝炎': 'Hepatitis',
    '愛滋病/人類免疫缺乏病毒感染': 'HIV/AIDS',
    'COVID-19': 'COVID-19',
    '瘧疾': 'Malaria',
    '肥胖症': 'Obesity',
    '甲狀腺疾病': 'Thyroid disorders',
    '阿茲海默症': "Alzheimer's disease",
    '帕金森氏症': "Parkinson's disease",
    '偏頭痛': 'Migraine',
    '癲癇': 'Epilepsy',
    '癌症': 'Cancer',
    '皮膚癌': 'Skin cancer',
    '乳癌': 'Breast cancer',
    '子宮頸癌': 'Cervical cancer',
    '白血病': 'Leukemia',
    '過敏': 'Allergies',
    '貧血': 'Anemia',
    '骨質疏鬆症': 'Osteoporosis',
    '關節炎': 'Arthritis',
    '憂鬱症': 'Depression',
    '焦慮症': 'Anxiety disorders',
    '胃食道逆流': 'GERD',
    '腸躁症': 'Irritable bowel syndrome',
    '乳糜瀉': 'Celiac disease',
    '慢性腎臟病': 'Chronic kidney disease',
    '慢性阻塞性肺病（COPD）': 'Chronic obstructive pulmonary disease',
    '肺炎': 'Pneumonia',
    '睡眠呼吸中止症': 'Sleep apnea',
    '腦中風': 'Stroke',
  };

  const inferTopicKey = (topic: string) => {
    const match = topic.match(/[（(]([A-Za-z0-9'\\-\\s\\/]+)[)）]/);
    if (match?.[1]) {
      const token = match[1].trim();
      if (token.toLowerCase() === 'copd') return 'Chronic obstructive pulmonary disease';
      return token;
    }
    return TOPIC_KEY_MAP[topic];
  };

  const handleTopicClick = (topic: string) => {
    setQuery(topic);
    setTopicKey(inferTopicKey(topic) || '');
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-cyan-50/50 to-teal-50/50">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-5 h-5 text-cyan-600" />
          <h2 className="text-lg font-semibold text-slate-900">
            提出您的醫學問題
          </h2>
        </div>
        <p className="text-sm text-slate-600">
          輸入自然語言醫學問題，或從下方主題建議中選擇
        </p>
      </div>

      <div className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Query Type Selection */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">
              問題類型
            </label>
            <div className="flex flex-wrap gap-2">
              {queryTypes.map((type) => {
                const Icon = type.icon;
                const isSelected = queryType === type.type;
                return (
                  <button
                    key={type.type}
                    type="button"
                    onClick={() => setQueryType(type.type)}
                    disabled={disabled}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'bg-cyan-50 border-cyan-500 text-cyan-700 shadow-sm'
                        : 'bg-white border-slate-200 text-slate-600 hover:border-cyan-300 hover:bg-cyan-50/50'
                    } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{type.label}</span>
                    {isSelected && (
                      <div className="w-2 h-2 bg-cyan-500 rounded-full"></div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例如：糖尿病的症狀有哪些？如何預防心臟病？COVID-19的最新治療方法是什麼？"
              className="min-h-[120px] resize-none text-base focus-visible:ring-cyan-500"
              disabled={disabled}
            />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {query.length} 字元
            </span>
            <Button
              type="submit"
              disabled={!query.trim() || disabled}
              className="bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>分析中...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>提交查詢</span>
                </>
              )}
            </Button>
          </div>
        </form>

        {/* Topic Suggestions */}
        <div className="mt-6 pt-6 border-t border-slate-100">
          <TopicSuggestions onTopicClick={handleTopicClick} />
        </div>
      </div>
    </div>
  );
}
