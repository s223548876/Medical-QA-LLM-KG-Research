import { useState } from 'react';
import { Badge } from './ui/badge';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface TopicCategory {
  category: string;
  topics: string[];
  icon: string;
}

const topicCategories: TopicCategory[] = [
  {
    category: '呼吸系統',
    icon: '🫁',
    topics: ['氣喘', '慢性阻塞性肺病（COPD）', '肺炎', '睡眠呼吸中止症'],
  },
  {
    category: '感染性疾病',
    icon: '🦠',
    topics: [
      '流行性感冒',
      '結核病',
      '肝炎',
      '愛滋病/人類免疫缺乏病毒感染',
      'COVID-19',
      '瘧疾',
    ],
  },
  {
    category: '代謝與內分泌',
    icon: '⚡',
    topics: ['糖尿病', '肥胖症', '甲狀腺疾病'],
  },
  {
    category: '心血管與腦血管疾病',
    icon: '❤️',
    topics: ['心臟病', '高血壓', '腦中風'],
  },
  {
    category: '神經系統疾病',
    icon: '🧠',
    topics: ['阿茲海默症', '帕金森氏症', '偏頭痛', '癲癇'],
  },
  {
    category: '腫瘤學（癌症）',
    icon: '🎗️',
    topics: ['癌症', '皮膚癌', '乳癌', '子宮頸癌', '白血病'],
  },
  {
    category: '免疫、血液與過敏',
    icon: '🛡️',
    topics: ['過敏', '貧血'],
  },
  {
    category: '骨骼與肌肉疾病',
    icon: '🦴',
    topics: ['骨質疏鬆症', '關節炎'],
  },
  {
    category: '身心醫學',
    icon: '🧘',
    topics: ['憂鬱症', '焦慮症'],
  },
  {
    category: '消化系統疾病',
    icon: '🫃',
    topics: ['胃食道逆流', '腸躁症', '乳糜瀉'],
  },
  {
    category: '泌尿與腎臟疾病',
    icon: '💧',
    topics: ['慢性腎臟病'],
  },
];

interface TopicSuggestionsProps {
  onTopicClick: (topic: string) => void;
}

export function TopicSuggestions({ onTopicClick }: TopicSuggestionsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['代謝與內分泌', '心血管與腦血管疾病'])
  );

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  return (
    <div>
      <h3 className="text-sm font-medium text-slate-700 mb-3">
        💡 常見主題建議
      </h3>
      <div className="grid md:grid-cols-2 gap-2">
        {topicCategories.map((category) => {
          const isExpanded = expandedCategories.has(category.category);
          return (
            <div
              key={category.category}
              className="border border-slate-200 rounded-lg overflow-hidden bg-slate-50/50"
            >
              <button
                onClick={() => toggleCategory(category.category)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-100/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{category.icon}</span>
                  <span className="text-sm font-medium text-slate-800">
                    {category.category}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    {category.topics.length}
                  </Badge>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                )}
              </button>
              {isExpanded && (
                <div className="px-4 pb-3 pt-1 bg-white">
                  <div className="flex flex-wrap gap-2">
                    {category.topics.map((topic) => (
                      <button
                        key={topic}
                        onClick={() => onTopicClick(topic)}
                        className="px-3 py-1.5 text-sm bg-white border border-cyan-200 text-cyan-700 rounded-full hover:bg-cyan-50 hover:border-cyan-300 transition-colors"
                      >
                        {topic}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}