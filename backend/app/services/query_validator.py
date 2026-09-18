# app/services/query_validator.py

import re
import logging
from typing import Dict, Tuple, Optional
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)


class StudyQueryValidator:
    """
    Validates if user queries are study-related before processing with Gemini API.
    Implements multiple validation layers for robust filtering.
    """

    # Keywords indicating study-related queries
    STUDY_KEYWORDS = {
        'education', 'learn', 'study', 'homework', 'assignment', 'exam', 'test',
        'quiz', 'course', 'class', 'lecture', 'tutorial', 'lesson', 'subject',
        'math', 'mathematics', 'science', 'history', 'literature', 'physics',
        'chemistry', 'biology', 'algebra', 'calculus', 'geometry', 'grammar',
        'essay', 'research', 'thesis', 'dissertation', 'paper', 'project',
        'presentation', 'explain', 'solve', 'calculate', 'define', 'describe',
        'analyze', 'compare', 'summarize', 'understand', 'concept', 'theory',
        'formula', 'equation', 'proof', 'theorem', 'law', 'principle', 'problem',
        'question', 'answer', 'solution', 'help', 'teach', 'show', 'demonstrate',
        'what is', 'how to', 'why does', 'when did', 'where is', 'who was',
        'vocabulary', 'meaning', 'definition', 'example', 'practice', 'review',
        'prepare', 'preparation', 'chapter', 'topic', 'notes', 'revision',
        'summarize', 'summary', 'key points', 'main idea', 'learning',
        'programming', 'coding', 'algorithm', 'data structure', 'computer science',
        'economics', 'psychology', 'sociology', 'philosophy', 'geography',
        'anatomy', 'physiology', 'engineering', 'architecture', 'statistics',
        'quadratic', 'derivative', 'integral', 'photosynthesis', 'newton', 'laws'
    }

    # Patterns indicating non-study queries (ONLY block obvious non-study content)
    REJECT_PATTERNS = [
        r'^(hi|hello|hey|sup|yo|wassup|howdy)[\s\?!]*$',  # Just greetings
        r'^(ok|okay|thanks|bye|good|nice)[\s\?!]*$',  # Simple responses
        r'^[a-z]{1,4}[\s\?!]*$',  # Very short single words like "maggie?"
    ]

    def __init__(self, use_ai_validation: bool = True, strict_mode: bool = False):
        """
        Initialize validator.

        Args:
            use_ai_validation: Use Gemini for semantic validation (recommended)
            strict_mode: Require both keyword AND AI validation to pass
        """
        self.use_ai_validation = use_ai_validation
        self.strict_mode = strict_mode

        # Configure Gemini API
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)

            if use_ai_validation:
                # Use lightweight model for validation to save tokens
                self.validator_model = genai.GenerativeModel(settings.gemini_model)

            # Main model for answering study queries
            self.study_model = genai.GenerativeModel(settings.gemini_model)

            logger.info("StudyQueryValidator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize StudyQueryValidator: {e}")
            raise

    def keyword_validation(self, query: str) -> bool:
        """
        Fast keyword-based validation (first layer).

        Returns:
            True if query contains study-related keywords OR looks like a question
        """
        query_lower = query.lower()

        # Check for reject patterns first (very strict - only obvious non-study)
        for pattern in self.REJECT_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug(f"Query rejected by pattern: {pattern}")
                return False

        # Check for study keywords
        has_keywords = any(keyword in query_lower for keyword in self.STUDY_KEYWORDS)

        # Also allow questions (contains "?", "what", "how", "why", etc.)
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'explain', 'solve', 'help', 'teach']
        has_question = '?' in query or any(word in query_lower for word in question_words)

        # Allow longer queries (likely to be study-related)
        is_substantial = len(query.split()) >= 4

        if has_keywords or has_question or is_substantial:
            logger.debug("Query passed keyword validation")
            return True

        logger.debug("Query failed keyword validation")
        return False

    def ai_validation(self, query: str) -> Tuple[bool, str]:
        """
        AI-powered semantic validation (second layer).

        Returns:
            Tuple of (is_valid, reason)
        """
        validation_prompt = f"""You are a query classifier for an educational AI assistant. Determine if this query is study/education-related.

Query: "{query}"

A query is STUDY-RELATED if it asks about:
- Academic subjects (math, science, history, languages, literature, arts, computer science, etc.)
- Learning concepts, theories, explanations, or educational content
- Homework, assignments, exams, quizzes, or test preparation
- Problem solving, calculations, or step-by-step solutions
- Understanding concepts or learning new skills
- ANY question that could help someone learn or understand something

Examples of VALID queries:
- "Help me solve quadratic equations"
- "Explain photosynthesis"
- "What is Newton's first law?"
- "How do I calculate derivatives?"

A query is NOT study-related ONLY if it's clearly about:
- Simple greetings without questions (just "hi", "hello")
- Random words or names without context (like "maggie?")
- Entertainment, gossip, or casual chat
- Inappropriate or harmful content

BE GENEROUS - if there's ANY educational value, mark it as VALID.

Respond in this exact format:
VALID: yes/no
REASON: [brief explanation]"""

        try:
            response = self.validator_model.generate_content(
                validation_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=100
                )
            )

            result = response.text.strip()

            # Parse response
            is_valid = 'VALID: yes' in result.lower() or 'valid: yes' in result.lower()
            reason_match = re.search(r'REASON:\s*(.+)', result, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "Classification complete"

            logger.debug(f"AI validation result: {is_valid} - {reason}")

            return is_valid, reason

        except Exception as e:
            logger.warning(f"AI validation error: {e}. Falling back to keyword validation.")
            # If AI fails, be permissive and allow the query
            return True, "AI validation unavailable, allowing query"

    def validate_query(self, query: str) -> Dict:
        """
        Main validation method combining all layers.

        Returns:
            Dict with validation result and metadata
        """
        query = query.strip()

        # Empty query check
        if not query or len(query) < 3:
            return {
                'valid': False,
                'reason': 'Query too short or empty',
                'method': 'basic'
            }

        # Layer 1: Keyword validation (fast, no API call)
        keyword_valid = self.keyword_validation(query)

        # If keyword validation passes, accept immediately in flexible mode
        if keyword_valid and not self.strict_mode:
            return {
                'valid': True,
                'reason': 'Query appears to be study-related',
                'method': 'keyword',
                'keyword_passed': True
            }

        # Layer 2: AI validation (semantic understanding)
        if self.use_ai_validation:
            try:
                ai_valid, ai_reason = self.ai_validation(query)

                if self.strict_mode:
                    final_valid = keyword_valid and ai_valid
                    method = 'keyword+ai_strict'
                else:
                    # In flexible mode, pass if EITHER validates
                    final_valid = keyword_valid or ai_valid
                    method = 'keyword+ai_flexible'

                if not final_valid:
                    logger.info(f"Query rejected by validation: {query[:50]}...")

                return {
                    'valid': final_valid,
                    'reason': ai_reason if not final_valid else 'Query validated as study-related',
                    'method': method,
                    'keyword_passed': keyword_valid,
                    'ai_passed': ai_valid
                }
            except Exception as e:
                logger.error(f"Validation error: {e}. Allowing query to proceed.")
                # If validation fails, be permissive
                return {
                    'valid': True,
                    'reason': 'Validation error, allowing query',
                    'method': 'error_fallback'
                }

        return {
            'valid': keyword_valid,
            'reason': 'Based on keyword analysis',
            'method': 'keyword_only'
        }

    def process_query(self, query: str, context: Optional[str] = None) -> Dict:
        """
        Complete pipeline: validate and process study queries.

        Args:
            query: User's question
            context: Optional context/history for the query

        Returns:
            Dict with response or rejection message
        """
        # Validate query
        try:
            validation = self.validate_query(query)
        except Exception as e:
            logger.error(f"Validation error: {e}. Processing query anyway.")
            validation = {'valid': True, 'reason': 'Validation error, proceeding', 'method': 'error_bypass'}

        if not validation['valid']:
            logger.info(f"Rejected query: {query[:100]}... | Reason: {validation['reason']}")
            return {
                'success': False,
                'message': 'This assistant only answers study-related questions. Please ask about academic subjects like math, science, history, or other educational topics.',
                'details': validation['reason'],
                'query': query,
                'validation': validation
            }

        # Process valid study query with Gemini
        try:
            logger.info(f"Processing valid study query: {query[:100]}...")

            prompt = "You are a helpful study assistant. Answer this educational query clearly and accurately:\n\n"

            if context:
                prompt += f"Context: {context}\n\n"

            prompt += f"Question: {query}"

            response = self.study_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048
                )
            )

            logger.info("Query processed successfully")

            return {
                'success': True,
                'response': response.text,
                'validation': validation,
                'query': query
            }

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                'success': False,
                'message': 'Error processing your study question. Please try again.',
                'details': str(e),
                'query': query
            }


# Singleton instance
_validator_instance: Optional[StudyQueryValidator] = None


def get_validator(use_ai_validation: bool = True, strict_mode: bool = False) -> StudyQueryValidator:
    """Get or create the validator singleton instance."""
    global _validator_instance

    if _validator_instance is None:
        _validator_instance = StudyQueryValidator(
            use_ai_validation=use_ai_validation,
            strict_mode=strict_mode
        )

    return _validator_instance