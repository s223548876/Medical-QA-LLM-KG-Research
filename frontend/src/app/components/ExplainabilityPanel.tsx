import { Answer } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import {
  Network,
  GitBranch,
  Database,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';
import { motion } from 'motion/react';

interface ExplainabilityPanelProps {
  answer: Answer;
  isOpen: boolean;
  onToggle: () => void;
}

export function ExplainabilityPanel({
  answer,
  isOpen,
  onToggle,
}: ExplainabilityPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
    >
      <Card className="border-purple-200 bg-gradient-to-br from-purple-50/50 to-indigo-50/30">
        <Collapsible open={isOpen} onOpenChange={onToggle}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-purple-50/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center">
                    <Network className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">可解釋性分析</CardTitle>
                    <p className="text-sm text-slate-600 mt-0.5">
                      深入了解系統推理過程與知識圖譜結構
                    </p>
                  </div>
                </div>
                <motion.div
                  animate={{ rotate: isOpen ? 180 : 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                </motion.div>
              </div>
            </CardHeader>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <CardContent className="pt-0 space-y-6">
              {/* Medical Entities */}
              <div className="bg-white rounded-lg border border-slate-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Database className="w-5 h-5 text-cyan-600" />
                  <h3 className="font-semibold text-slate-900">
                    已識別的醫學實體
                  </h3>
                  <Badge variant="secondary" className="text-xs">
                    {answer.entities.length} 個
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {answer.entities.map((entity, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="text-sm bg-cyan-50 text-cyan-700 border-cyan-200 py-1.5 px-3"
                    >
                      {entity}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* SNOMED CT Concepts */}
              <div className="bg-white rounded-lg border border-slate-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <GitBranch className="w-5 h-5 text-teal-600" />
                  <h3 className="font-semibold text-slate-900">
                    映射的 SNOMED CT 概念
                  </h3>
                  <Badge variant="secondary" className="text-xs">
                    標準化醫學術語
                  </Badge>
                </div>
                <div className="space-y-2">
                  {answer.snomedConcepts.map((concept, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-teal-50/50 rounded-lg border border-teal-100"
                    >
                      <div className="w-6 h-6 bg-teal-500 text-white rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-slate-900 text-sm">
                          {concept.concept}
                        </p>
                        <p className="text-xs text-slate-600 mt-1 font-mono bg-white px-2 py-1 rounded inline-block">
                          {concept.code}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Subgraph Summary */}
              <div className="bg-white rounded-lg border border-slate-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Network className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold text-slate-900">子圖摘要</h3>
                  <Badge variant="secondary" className="text-xs">
                    知識圖譜結構
                  </Badge>
                </div>
                <div className="p-4 bg-purple-50/50 rounded-lg border border-purple-100">
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {answer.subgraphSummary}
                  </p>
                </div>
              </div>

              {/* Reasoning Path */}
              <div className="bg-white rounded-lg border border-slate-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <ArrowRight className="w-5 h-5 text-indigo-600" />
                  <h3 className="font-semibold text-slate-900">推理路徑</h3>
                  <Badge variant="secondary" className="text-xs">
                    系統處理流程
                  </Badge>
                </div>
                <div className="space-y-3">
                  {answer.reasoningPath.map((step, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className="flex items-start gap-3"
                    >
                      <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-full flex-shrink-0 text-sm font-semibold">
                        {idx + 1}
                      </div>
                      <div className="flex-1 pt-1">
                        <p className="text-sm text-slate-700">{step}</p>
                      </div>
                      {idx < answer.reasoningPath.length - 1 && (
                        <div className="absolute left-4 mt-8 w-0.5 h-6 bg-gradient-to-b from-indigo-200 to-purple-200 ml-0"></div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>

            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    </motion.div>
  );
}
