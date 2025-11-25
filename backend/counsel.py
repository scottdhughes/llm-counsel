"""3-stage Legal Counsel deliberation orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNSEL_MODELS, LEAD_COUNSEL_MODEL


async def stage1_collect_responses(legal_question: str, context: str = None) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual legal strategy responses from all counsel models.

    Args:
        legal_question: The legal question or issue to analyze
        context: Additional case context (optional)

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    # Build the legal strategy prompt
    prompt = f"""You are a senior legal strategist providing a detailed strategy memorandum for the following legal question:

LEGAL QUESTION:
{legal_question}"""

    if context:
        prompt += f"""

CASE CONTEXT:
{context}"""

    prompt += """

Prepare a comprehensive LEGAL STRATEGY MEMORANDUM in the following format:

## I. EXECUTIVE SUMMARY
- Brief 2-3 sentence overview of the issue and recommended approach

## II. LEGAL FRAMEWORK & APPLICABLE LAW
- Relevant statutes, regulations, and case law
- Key legal principles and standards
- Jurisdictional considerations

## III. LEGAL ANALYSIS
A. **Key Issues Identified**
   - List and explain each legal issue

B. **Strengths of Position**
   - Arguments in our favor
   - Supporting authority
   - Favorable facts

C. **Weaknesses & Challenges**
   - Potential counterarguments
   - Unfavorable precedent
   - Evidentiary gaps or concerns

## IV. STRATEGIC RECOMMENDATIONS
A. **Primary Strategy**
   - Recommended course of action with detailed rationale

B. **Alternative Approaches**
   - Backup strategies if primary approach fails

C. **Tactical Considerations**
   - Timing, venue, procedural moves

## V. RISK ASSESSMENT & MITIGATION
- Key risks (legal, procedural, practical)
- Likelihood and impact of each risk
- Specific mitigation strategies

## VI. ACTION ITEMS & NEXT STEPS
Priority-ordered list with:
- Immediate actions (within 7 days)
- Short-term actions (within 30 days)
- Long-term strategic items

Be specific, cite relevant authority where applicable (cases, statutes, regulations), and provide concrete, actionable guidance. Write in a professional legal memorandum style."""

    messages = [{"role": "user", "content": prompt}]

    # Query all models in parallel
    responses = await query_models_parallel(COUNSEL_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    legal_question: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized legal strategy responses.

    Args:
        legal_question: The original legal question
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different legal strategy analyses for this question:

Question: {legal_question}

Here are the legal strategy analyses from different sources (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each analysis, explain:
   - Legal soundness and accuracy
   - Strength of strategic recommendations
   - Practical viability of proposed approach
   - Completeness of analysis

2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides solid legal analysis but lacks depth on procedural strategy...
Response B offers comprehensive coverage of risks and mitigation strategies...
Response C has good practical recommendations but misses key legal authorities...

FINAL RANKING:
1. Response B
2. Response A
3. Response C

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all counsel models in parallel
    responses = await query_models_parallel(COUNSEL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    legal_question: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Lead Counsel synthesizes final legal strategy recommendation.

    Args:
        legal_question: The original legal question
        stage1_results: Individual analyses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for Lead Counsel
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nAnalysis: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nEvaluation: {result['ranking']}"
        for result in stage2_results
    ])

    lead_counsel_prompt = f"""You are the Lead Counsel for this matter. Multiple senior legal strategists have independently analyzed the legal question and peer-reviewed each other's work. Your role is to synthesize their collective wisdom into a definitive strategy memorandum.

═══════════════════════════════════════════════════════
LEGAL QUESTION UNDER REVIEW:
{legal_question}
═══════════════════════════════════════════════════════

DELIBERATION RECORD:

STAGE 1 - Independent Counsel Analyses:
{stage1_text}

STAGE 2 - Peer Evaluations & Rankings:
{stage2_text}

═══════════════════════════════════════════════════════

As Lead Counsel, prepare a FINAL STRATEGY MEMORANDUM using this structure:

# LEAD COUNSEL STRATEGY MEMORANDUM

## I. EXECUTIVE SUMMARY
Provide a concise (3-4 sentences) overview synthesizing:
- The core legal issue
- Recommended strategic approach
- Expected outcome and key risks

## II. CONSENSUS LEGAL ANALYSIS

### A. Governing Legal Framework
- Synthesize the applicable statutes, regulations, and case law identified by counsel
- Note any areas of agreement or disagreement among the team
- Clarify the correct legal standard(s) to apply

### B. Strength Assessment
Integrate the strongest arguments identified across all analyses:
- What are our best legal arguments?
- What facts support our position?
- Which precedents favor us?

### C. Vulnerabilities & Challenges
Based on collective assessment:
- What are our weakest points?
- What counterarguments must we address?
- Where do we face evidentiary or procedural hurdles?

## III. STRATEGIC RECOMMENDATION (PRIMARY)

### Recommended Course of Action:
- Clearly state the recommended strategy
- Explain WHY this approach is optimal (integrate counsel insights)
- Address how it leverages our strengths while mitigating weaknesses

### Implementation Plan:
- Specific tactical steps in logical sequence
- Timing considerations
- Resource requirements

## IV. ALTERNATIVE STRATEGIES CONSIDERED

Briefly discuss why alternative approaches were not selected as primary strategy:
- What other options did counsel suggest?
- Why are they secondary to the primary recommendation?
- Under what circumstances might we pivot to these alternatives?

## V. RISK MATRIX & MITIGATION

| Risk Category | Likelihood | Impact | Mitigation Strategy |
|--------------|-----------|--------|-------------------|
| [Identify each major risk with concrete mitigation plans] |

## VI. AREAS REQUIRING RESOLUTION

Note any:
- Factual gaps requiring investigation
- Legal issues needing additional research
- Strategic decisions requiring client input
- Points where counsel disagreed that need client direction

## VII. PRIORITIZED ACTION PLAN

**IMMEDIATE (0-7 Days):**
1. [Most urgent action with deadline]
2. [Next priority]

**SHORT-TERM (7-30 Days):**
1. [Important follow-up actions]

**ONGOING/STRATEGIC:**
1. [Longer-term initiatives]

## VIII. CONCLUSION
One paragraph bottom-line assessment and recommendation.

---

**IMPORTANT:** This is the FINAL work product for the client. Write with authority, clarity, and professionalism. Synthesize—don't just summarize. Where counsel disagreed, make a definitive call based on the weight of legal authority and strategic considerations. Provide specific, actionable guidance."""

    messages = [{"role": "user", "content": lead_counsel_prompt}]

    # Query the Lead Counsel model
    response = await query_model(LEAD_COUNSEL_MODEL, messages)

    if response is None:
        # Fallback if Lead Counsel fails
        return {
            "model": LEAD_COUNSEL_MODEL,
            "response": "Error: Unable to generate final strategy synthesis."
        }

    return {
        "model": LEAD_COUNSEL_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def run_full_counsel(legal_question: str, context: str = None) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage legal counsel deliberation process.

    Args:
        legal_question: The legal question or issue to analyze
        context: Additional case context (optional)

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual legal strategy responses
    stage1_results = await stage1_collect_responses(legal_question, context)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(legal_question, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final legal strategy
    stage3_result = await stage3_synthesize_final(
        legal_question,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
