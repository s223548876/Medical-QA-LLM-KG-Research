# Medical-QA-LLM-KG-Research
Research prototype for a medical question answering system based on LLMs and medical knowledge graphs.

# 基於大型語言模型與醫療知識圖譜之醫療問答系統

本專案為一套**研究導向的實驗型醫療問答系統（research prototype）**，  
用於碩士論文中探討 **大型語言模型（Large Language Models, LLMs）結合醫療知識圖譜（Knowledge Graph, KG）**  
在醫療問答任務中的效能與回答品質差異。

⚠️ **本系統僅供學術研究與實驗評估使用，並非實際醫療系統，亦不可用於任何臨床診斷或醫療決策。**

---

## 一、研究動機與目標

近年來大型語言模型在自然語言理解與生成任務上展現出顯著成效，並逐漸被應用於醫療問答情境。然而，純 LLM 模型在醫療領域中仍面臨以下問題：

- 可能產生幻覺（hallucination）
- 缺乏結構化醫學知識支撐
- 回答一致性與可解釋性不足

本研究旨在探討：

> **透過引入醫療知識圖譜輔助，是否能提升大型語言模型於醫療問答任務中的回答品質與穩定性。**

---

## 二、系統定位與研究範圍

本專案之系統定位為：

> **研究導向的實驗平台（Experimental Research System）**

其主要用途為：
- 比較不同問答策略（LLM-only 與 LLM+KG）
- 進行自動化與人工評估實驗
- 分析不同題型下的回答表現差異

**本系統並非：**
- 對外公開之醫療服務
- 臨床決策支援系統
- 可供一般民眾長期使用之醫療諮詢工具

---

## 三、系統架構概述

整體系統流程包含以下模組：

1. **問題輸入（Question Input）**
2. **醫學實體辨識（Medical Entity Recognition）**
   - 使用 scispaCy 進行醫學實體擷取
3. **醫學概念對應（Concept Mapping）**
   - 將實體對應至 SNOMED CT 概念編號
4. **知識圖譜子圖擷取（Subgraph Retrieval）**
   - 以 is-a 階層關係為核心
5. **回答生成策略**
   - LLM-only（純語言模型）
   - LLM+KG（知識圖譜輔助生成）
6. **回答輸出與格式控制**

> 本系統目前僅使用 SNOMED CT 中之分類（is-a）關係，  
> 症狀與治療類問題主要透過語言模型生成與提示設計處理。

---

## 四、實驗資料集

本研究使用 MedlinePlus 作為標準參考資料來源，建構兩組醫療問答資料集：

### 1. 主資料集（Main Dataset）
- 題目數量：105 題
- 主題數量：35 個疾病主題
- 題型：
  - 疾病定義（Definition）
  - 症狀描述（Symptoms）
  - 治療方式（Treatments）

### 2. 擴展資料集（Extended Dataset）
- 題目數量：858 題（經資料清洗後）
- 用於驗證系統在較大規模資料下的穩定性

⚠️ **基於資料授權與使用限制，本 repository 不直接提供資料集內容。**

---

## 五、評估方法

本研究採用多種評估方式，以全面分析系統表現：

### （一）自動化評估
- ROUGE-1
- ROUGE-L
- BERTScore
- Bootstrap 重抽樣信賴區間（2,000 次）

### （二）人工評估
- A/B 回答對照評估（LLM-only vs LLM+KG）
- 評估面向包含：
  - 正確性
  - 完整性
  - 可理解性
- 問卷方式蒐集評分結果

### （三）LLM-as-a-Judge
- 使用 GPT-4o mini 作為評分模型
- 評估模型回答與標準答案之相似程度

---
