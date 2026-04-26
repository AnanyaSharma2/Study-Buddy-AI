from langchain_core.output_parsers import PydanticOutputParser
from src.models.questions_schema import MCQQuestion,FillBlankQuestion,ShortAnswerQuestion
from src.prompts.template import mcq_prompt_template,fill_blank_prompt_template,short_answer_prompt_template 
from src.llm.groq_client import get_groq_llm
from src.config.settings import settings
from src.common.logger import get_logger
from src.common.custom_exception import CustomException


class QuestionGenerator:

    def __init__(self):
        self.llm = get_groq_llm()
        self.logger = get_logger(self.__class__.__name__)

    # ================= CORE ENGINE =================
    def _retry_and_parse(self, prompt, parser, topic, difficulty):

        for attempt in range(settings.MAX_RETRIES):
            try:
                self.logger.info(f"Generating {topic} ({difficulty}) attempt {attempt+1}")

                response = self.llm.invoke(
                    prompt.format(topic=topic, difficulty=difficulty)
                )

                # 🔥 Clean markdown if present
                content = response.content.replace("```json", "").replace("```", "").strip()

                parsed = parser.parse(content)

                self.logger.info("Successfully parsed the question")
                return parsed

            except Exception as e:
                self.logger.error(f"Error: {str(e)}")

                if attempt == settings.MAX_RETRIES - 1:
                    raise CustomException(
                        f"Failed after {settings.MAX_RETRIES} attempts",
                        e
                    )

    # ================= MCQ =================
    def generate_mcq(self, topic: str, difficulty: str = 'medium') -> MCQQuestion:
        try:
            parser = PydanticOutputParser(pydantic_object=MCQQuestion)

            question = self._retry_and_parse(
                mcq_prompt_template,
                parser,
                topic,
                difficulty
            )

            self.logger.info("Valid MCQ generated")
            return question

        except Exception as e:
            self.logger.error(f"MCQ failed: {str(e)}")
            raise CustomException("MCQ generation failed", e)

    # ================= Fill Blank =================
    def generate_fill_blank(self, topic: str, difficulty: str = 'medium') -> FillBlankQuestion:
        try:
            parser = PydanticOutputParser(pydantic_object=FillBlankQuestion)

            question = self._retry_and_parse(
                fill_blank_prompt_template,
                parser,
                topic,
                difficulty
            )

            if "___" not in question.question:
                raise ValueError("Missing blank (___)")

            self.logger.info("Valid Fill Blank generated")
            return question

        except Exception as e:
            self.logger.error(f"Fill blank failed: {str(e)}")
            raise CustomException("Fill blank generation failed", e)

    # ================= Short Answer =================
    def generate_short_answer(self, topic: str, difficulty: str = 'medium') -> ShortAnswerQuestion:
        try:
            parser = PydanticOutputParser(pydantic_object=ShortAnswerQuestion)

            question = self._retry_and_parse(
                short_answer_prompt_template,
                parser,
                topic,
                difficulty
            )

            if not question.answer.strip():
                raise ValueError("Empty answer")

            if len(question.answer.split()) > 30:
                raise ValueError("Answer too long")

            self.logger.info("Valid Short Answer generated")
            return question

        except Exception as e:
            self.logger.error(f"Short answer failed: {str(e)}")
            raise CustomException("Short answer generation failed", e)