"""提案分析相关的提示词模板"""

ANALYSIS_TEMPLATE = """
请对以下提案进行分析评估:

提案标题: {proposal_title}
提案内容: {proposal_content}

请分析以下方面并以JSON格式返回:
1. 各维度评分(1-10分):
   - 可行性(feasibility)
   - 相关性(relevance)
   - 成本效益(cost_benefit)
   - 影响力(impact)
   - 风险(risk)
2. 整体评分(overall_score)
3. 优势(strengths)和弱点(weaknesses)
4. 潜在风险(risks)

仅返回JSON格式，不要有其他文字。
"""

VOTE_TEMPLATE = """
根据以下提案分析结果，决定是支持(support)还是反对(oppose)该提案:

{analysis_result}

请以JSON格式返回你的决定，包含以下字段:
1. vote_type: "support"或"oppose"
2. reason: 决定的详细理由
3. confidence: 决策置信度(0-1)

仅返回JSON格式，不要有其他文字。
"""

COMMENT_TEMPLATE = """
根据以下提案分析结果，生成一段评论:

{analysis_result}

评论情感倾向: {sentiment} (positive/negative/neutral)

请以JSON格式返回评论，包含以下字段:
1. content: 评论正文
2. highlights: 提案亮点
3. suggestions: 改进建议

仅返回JSON格式，不要有其他文字。
"""