import rich.box
import textwrap
import yaml
from rich.markdown import Markdown
from rich.panel import Panel
from smah.console import std_console
import logging
from typing import Optional, Any, Dict
from dataclasses import dataclass

# Constants
MAX_PIPE_LENGTH = 2048
PIPE_HEAD_LENGTH = 1024

@dataclass
class PickerOutput:
    pick_model: Any
    pick_reason: str
    include_context: bool
    include_context_reason: str
    raw_output: bool
    raw_output_reason: str

class Runner:
    @staticmethod
    def __print_query_mode() -> None:
        std_console.print(Panel("Processing In Query Mode", title="Query", style="bold white", box=rich.box.ROUNDED))

    @staticmethod
    def __create_pipe_request_content(query: str, pipe: str) -> str:
        if len(pipe) > MAX_PIPE_LENGTH:
            pipe_head = pipe[:PIPE_HEAD_LENGTH]
            pipe_tail = pipe[PIPE_HEAD_LENGTH:]
            request_template = textwrap.dedent(
                """
                # Pipe Request
                {query}
                ----
                Pipe:
                {pipe_head}
                .
                . (anything may be here, it may not be the same content as in the head or tail of stream)
                .
                {pipe_tail}
                """
            ).format(query=query, pipe_head=pipe_head, pipe_tail=pipe_tail)
        else:
            request_template = textwrap.dedent(
                """
                # Pipe Request
                {query}
                ----
                Pipe:
                {pipe}
                """
            ).format(query=query, pipe=pipe)
        return request_template.strip()


    @staticmethod
    def __display_picker_response(picker_output: PickerOutput, query_dict: dict) -> None:
        picker_response = textwrap.dedent(
            f"""
            picker: {picker_output.pick_model.model}
            selected_model: {picker_output.pick_model.model}
            reason: {picker_output.pick_reason}
            include_context: {picker_output.include_context}
            include_context_reason: {picker_output.include_context_reason}
            raw_output: {picker_output.raw_output}
            raw_output_reason: {picker_output.raw_output_reason}
            """)
        q = Panel(picker_response, title="Model Picker", style="bold yellow", box=rich.box.SQUARE)
        std_console.print(q)

        q = Panel(query_dict['content'], title="Query", style="bold white", box=rich.box.ROUNDED)
        std_console.print(q)

    @staticmethod
    def __display_response(response: str, raw_output: bool = False) -> None:
        q = Panel("LLM Response Below", title="Response", style="bold yellow", box=rich.box.ROUNDED)
        std_console.print(q)

        if raw_output:
            print(response)
        else:
            m = Markdown(response)
            std_console.print(m)

    def __init__(self, args: Any, settings: Any) -> None:
        self.args = args
        self.settings = settings

    def query(self, query: str) -> None:
        try:
            picker_model = self.settings.providers.picker_model()
            self.__print_query_mode()

            query_dict = self.__compose_query_dict(query)
            pick = picker_model.pick(query_dict, self.settings)
            if pick is not None:
                picker_output = PickerOutput(*pick)
                self.__display_picker_response(picker_output, query_dict)
                response = picker_output.pick_model.query(query, picker_output.include_context, self.settings)
                self.__display_response(response)
        except Exception as e:
            logging.error(f"Error in query method: {str(e)}")

    def pipe(self, query: str, pipe: str) -> None:
        try:
            picker_model = self.settings.providers.picker_model()

            query = textwrap.dedent(query)
            request_content = self.__create_pipe_request_content(query, pipe)

            request_dict = {
                "role": "user",
                "content": request_content
            }

            pick = picker_model.pick(request_dict, self.settings)
            if pick is not None:
                picker_output = PickerOutput(*pick)
                self.__display_picker_response(picker_output, request_dict)
                response = picker_output.pick_model.pipe(query, pipe, picker_output.include_context, self.settings)
                self.__display_response(response, raw_output=picker_output.raw_output)
        except Exception as e:
            logging.error(f"Error in pipe method: {str(e)}")

    def interactive(self, pipe: Optional[str] = None) -> None:
        try:
            picker_model = self.settings.providers.picker_model()
            std_console.print("--- Interactive ---")
            std_console.print(f"Picker Model: {picker_model.model}")
            std_console.print("Interactive")
            std_console.print(f"Pipe: {pipe}")
        except Exception as e:
            logging.error(f"Error in interactive method: {str(e)}")

    def __compose_query_dict(self, query: str) -> Dict[str, str]:
        operator = self.settings.user.to_yaml() if self.settings.user is not None else None
        operator = yaml.dump(operator) if operator is not None else None

        q = textwrap.dedent(
            """
            # CLI User Request
            Your operator:
            {operator}
            has the following inquiry:
            ----
            {query}
            """).strip().format(operator=operator, query=query)
        return {"role": "user", "content": q}
