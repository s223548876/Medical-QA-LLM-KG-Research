import { Answer, ViewMode } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Skeleton } from './ui/skeleton';
import { Badge } from './ui/badge';
import { Bot, Network, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { motion } from 'motion/react';
import { useState } from 'react';

interface AnswerDisplayProps {
  answer: Answer | null;
  isLoading: boolean;
  viewMode: ViewMode;
  query: string;
}

export function AnswerDisplay({
  answer,
  isLoading,
  viewMode,
  query,
}: AnswerDisplayProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['symptoms', 'treatments'])
  );

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        <Card className="border-slate-200">
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-32 w-full mt-4" />
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  if (!answer) return null;

  // User Mode - Single Clear Answer
  if (viewMode === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="border-slate-200 shadow-md">
          <CardHeader className="bg-gradient-to-r from-cyan-50/50 to-teal-50/50 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-lg flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-lg">分析結果</CardTitle>
                <p className="text-sm text-slate-600 mt-1">關於「{query}」</p>
              </div>
              <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                ✓ 知識增強
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="prose prose-slate max-w-none">
              <div className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                {answer.kgLlm.split('\n').map((paragraph, idx) => {
                  if (paragraph.trim().startsWith('**') && paragraph.trim().endsWith('**')) {
                    const text = paragraph.trim().replace(/\*\*/g, '');
                    return (
                      <h3
                        key={idx}
                        className="text-base font-semibold text-slate-900 mt-6 mb-3 first:mt-0"
                      >
                        {text}
                      </h3>
                    );
                  }
                  if (paragraph.trim().startsWith('**') && paragraph.includes(':')) {
                    return (
                      <p key={idx} className="font-medium text-slate-800 mt-4 mb-2">
                        {paragraph}
                      </p>
                    );
                  }
                  if (paragraph.trim().startsWith('-')) {
                    return (
                      <li key={idx} className="ml-4 my-1 text-slate-700">
                        {paragraph.replace(/^-\s*/, '')}
                      </li>
                    );
                  }
                  if (paragraph.trim().match(/^\d+\./)) {
                    return (
                      <li key={idx} className="ml-4 my-1 text-slate-700">
                        {paragraph.replace(/^\d+\.\s*/, '')}
                      </li>
                    );
                  }
                  if (paragraph.trim()) {
                    return (
                      <p key={idx} className="my-3 text-slate-700">
                        {paragraph}
                      </p>
                    );
                  }
                  return null;
                })}
              </div>
            </div>

            {/* Key Terms Highlight */}
            <div className="mt-6 pt-6 border-t border-slate-100">
              <h4 className="text-sm font-medium text-slate-700 mb-3">
                🔑 關鍵醫學概念
              </h4>
              <div className="flex flex-wrap gap-2">
                {answer.entities.slice(0, 6).map((entity, idx) => (
                  <Badge
                    key={idx}
                    variant="outline"
                    className="text-cyan-700 border-cyan-200 bg-cyan-50/50"
                  >
                    {entity}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // Research Mode - Side-by-Side Comparison
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-lg font-semibold text-slate-900">
          系統比較分析
        </h2>
        <Badge variant="outline" className="text-xs">
          研究模式
        </Badge>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* LLM Only Answer */}
        <Card className="border-slate-200">
          <CardHeader className="bg-slate-50 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-slate-600 rounded-lg flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div>
                <CardTitle className="text-base">僅 LLM 答案</CardTitle>
                <p className="text-xs text-slate-600 mt-0.5">
                  純大型語言模型生成
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-sm text-slate-700 leading-relaxed space-y-3">
              {answer.llmOnly.split('\n').map((paragraph, idx) => {
                if (paragraph.trim().startsWith('**') && paragraph.trim().endsWith('**')) {
                  const text = paragraph.trim().replace(/\*\*/g, '');
                  return (
                    <h4
                      key={idx}
                      className="text-sm font-semibold text-slate-900 mt-4 mb-2 first:mt-0"
                    >
                      {text}
                    </h4>
                  );
                }
                if (paragraph.trim().startsWith('**')) {
                  return (
                    <p key={idx} className="font-medium text-slate-800 my-2">
                      {paragraph}
                    </p>
                  );
                }
                if (paragraph.trim().startsWith('-')) {
                  return (
                    <li key={idx} className="ml-4 my-1 text-slate-600 text-sm">
                      {paragraph.replace(/^-\s*/, '')}
                    </li>
                  );
                }
                if (paragraph.trim()) {
                  return (
                    <p key={idx} className="my-2 text-slate-600 text-sm">
                      {paragraph}
                    </p>
                  );
                }
                return null;
              })}
            </div>
          </CardContent>
        </Card>

        {/* KG + LLM Answer */}
        <Card className="border-cyan-200 ring-2 ring-cyan-100">
          <CardHeader className="bg-gradient-to-r from-cyan-50 to-teal-50 border-b border-cyan-100">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-lg flex items-center justify-center">
                <Network className="w-4 h-4 text-white" />
              </div>
              <div>
                <CardTitle className="text-base">知識圖譜 + LLM</CardTitle>
                <p className="text-xs text-cyan-700 mt-0.5">
                  結構化知識增強答案 ⭐
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-sm text-slate-700 leading-relaxed space-y-3">
              {answer.kgLlm.split('\n').map((paragraph, idx) => {
                if (paragraph.trim().startsWith('**') && paragraph.trim().endsWith('**')) {
                  const text = paragraph.trim().replace(/\*\*/g, '');
                  return (
                    <h4
                      key={idx}
                      className="text-sm font-semibold text-slate-900 mt-4 mb-2 first:mt-0"
                    >
                      {text}
                    </h4>
                  );
                }
                if (paragraph.trim().startsWith('**')) {
                  return (
                    <p key={idx} className="font-medium text-slate-800 my-2">
                      {paragraph}
                    </p>
                  );
                }
                if (paragraph.trim().startsWith('-')) {
                  return (
                    <li key={idx} className="ml-4 my-1 text-slate-600 text-sm">
                      {paragraph.replace(/^-\s*/, '')}
                    </li>
                  );
                }
                if (paragraph.trim().match(/^\d+\./)) {
                  return (
                    <li key={idx} className="ml-4 my-1 text-slate-600 text-sm">
                      {paragraph.replace(/^\d+\.\s*/, '')}
                    </li>
                  );
                }
                if (paragraph.trim()) {
                  return (
                    <p key={idx} className="my-2 text-slate-600 text-sm">
                      {paragraph}
                    </p>
                  );
                }
                return null;
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Reasoning Summary */}
      <Card className="border-slate-200 bg-slate-50/50">
        <CardHeader>
          <CardTitle className="text-base">🔍 系統推理摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-slate-800 mb-2">
                已識別醫學實體
              </h4>
              <div className="flex flex-wrap gap-2">
                {answer.entities.map((entity, idx) => (
                  <Badge
                    key={idx}
                    variant="secondary"
                    className="text-xs bg-white"
                  >
                    {entity}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <h4 className="font-medium text-slate-800 mb-2">
                SNOMED CT 概念映射
              </h4>
              <div className="space-y-1">
                {answer.snomedConcepts.slice(0, 3).map((concept, idx) => (
                  <div
                    key={idx}
                    className="text-xs text-slate-600 flex items-center gap-2"
                  >
                    <span className="w-2 h-2 bg-cyan-400 rounded-full"></span>
                    <span>
                      {concept.concept} ({concept.code})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
