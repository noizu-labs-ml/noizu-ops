import json
import logging
import textwrap

import rich.box
from typing import Optional, Tuple

import yaml
from openai import OpenAI, NotGiven, NOT_GIVEN
from openai.types.chat import ChatCompletion
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from smah.console import std_console, err_console
from smah.settings.inference.provider.model import Model
from smah.runner.prompts import Prompts
from smah.database import Database

class Runner:
    MAX_PIPE_LENGTH = 2048
    PIPE_HEAD_LENGTH = 1024


    @staticmethod
    def log_query_plan(plan: dict, level: int = logging.DEBUG, show: bool = False):
        plan = yaml.dump(plan, sort_keys=False)
        logging.log(level, f"Query Plan:\n{plan}")
        if show:
            err_console.print(Panel(
                Markdown("```yaml\n" + plan + "\n```\n"),
                title="Query Plan",
                style="bold yellow",
                box=rich.box.SQUARE)
            )

    @staticmethod
    def log_pipe_plan(plan: dict, level: int = logging.DEBUG, show: bool = False):
        plan = yaml.dump(plan, sort_keys=False)
        logging.log(level, f"Pipe Plan:\n{plan}")
        if show:
            err_console.print(Panel(
                Markdown("```yaml\n" + plan + "\n```\n"),
                title="Pipe Plan",
                style="bold yellow",
                box=rich.box.SQUARE)
            )

    @staticmethod
    def log_mode(mode: str, level: int = logging.INFO, show: bool = False) -> None:
        logging.log(level, f"Processing In {mode} Mode")
        if show:
            err_console.print(Panel(
                f"Processing In {mode} Mode",
                title="Mode",
                style="bold white",
                box=rich.box.ROUNDED)
            )


    @staticmethod
    def log_openai_completion_request(
            model: Model,
            thread: list,
            response_format: dict | NotGiven,
            options: Optional[dict] = None,
            show: bool = False,
            level: int = logging.INFO
    ) -> None:
        payload = yaml.dump(
            {
                'model': model.to_yaml(),
                'response_format': response_format if response_format != NOT_GIVEN else False,
                'options': options or False,
                'thread': thread
            },
            sort_keys=False
        )
        logging.log(level, f"OpenAI Completion Payload:\n{payload}")
        if show:
            err_console.print(Panel(
                Markdown("```yaml\n" + payload + "\n```\n"),
                title="OpenAI Completion Payload",
                style="bold white",
                box=rich.box.ROUNDED)
            )

    @staticmethod
    def log_openai_completion_response(response: ChatCompletion, level = logging.INFO, show: bool = False) -> None:
        payload = yaml.dump(
            response,
            sort_keys=False
        )
        logging.log(level, f"OpenAI Completion Response:\n{payload}")
        if show:
            err_console.print(Panel(
                Markdown("```yaml\n" + payload + "\n```\n"),
                title="OpenAI Completion Response",
                style="bold white",
                box=rich.box.ROUNDED)
            )

    @staticmethod
    def planner_response(response: ChatCompletion) -> Tuple[bool, dict] | None:
        plan = json.loads(response.choices[0].message.content)
        required_keys = ["title", "model", "reason", "include_settings", "include_settings_reason", "format_output",
                         "format_output_reason", "instructions"]
        if all(key in plan for key in required_keys):
            return True, plan
        else:
            missing_keys = [key for key in required_keys if key not in plan]
            logging.error(f"Missing keys: {missing_keys}")
            return None

    def __init__(self, args, settings):
        self.args = args
        self.settings = settings
        self.db = Database(args)




    def openai_client(self):
        api_key = self.settings.inference.providers['openai'].api_key(self.args)
        client = OpenAI(
            api_key=api_key
        )
        return client

    @staticmethod
    def print_message(message: dict, format: bool = False, styles: Optional[dict] = None):
        if format:
            styles = styles or {
                'assistant': 'bold white',
                'user': 'bold blue',
                'default': 'bold green'
            }
            style = styles.get(message['role'], styles.get('default','bold green'))
            std_console.print(
                Panel(Markdown(message['content']), title=message['role'], style=style, box=rich.box.ROUNDED)
            )
        else:
            std_console.print(f"--- {message['role']} ---")
            std_console.print(message['content'])



    def resume(self, id: int, title: str, plan: dict, pipe: str, messages: list) -> None:
        model_name = self.args.model or plan['model']
        model = self.settings.inference.models[model_name]
        open = textwrap.dedent(
            f"""
            Continue Session #{id} - {title}
            =========
            """
        )
        std_console.print(Markdown(open) if self.args.rich else open)

        thread = [
            Prompts.conventions(),
            Prompts.ack(),
            Prompts.system_settings(self.settings, include_system=plan['include_settings']),
            Prompts.ack(),
        ]

        if pipe:
            thread.append(Prompts.message(content=f"--- INPUT ---\n{pipe}"))
            thread.append(Prompts.ack())

        for message in messages:
            thread.append(Prompts.message(content=message['content'], role=message['role']))
            self.print_message(message, format=self.args.rich)

        query = Prompt.ask("[bold green]Message[/bold green]: (type 'exit' or enter to end session)")
        query = query.strip()
        while query != 'exit' and query:
            query_message = Prompts.message(content=query, role='user')
            self.print_message(query_message, format=self.args.rich)

            # Query with Instructions
            thread.append(Prompts.query_prompt(request=query))
            response = self.run(model, thread)

            # Response
            message = Prompts.message(role=response.choices[0].message.role, content=response.choices[0].message.content)
            self.print_message(message, format=self.args.rich)

            # Update Chat History
            self.db.append_to_chat(id, [query_message, message])

            # Continue
            query = Prompt.ask("[bold green]Message[/bold green]: (type 'exit' or enter to end session)")

        exit(0)

    def run(self,
            model: Model,
            thread: list,
            response_format: dict | NotGiven = NOT_GIVEN,
            options: Optional[dict] = None,
            show: bool = False
            ):
        options = options or {}
        if model.provider == "openai":
            self.log_openai_completion_request(
                model=model,
                thread=thread,
                response_format=response_format,
                options=options,
                show=show
                )

            client = self.openai_client()
            model_settings = model.settings or {}

            max_output_tokens = model.context.get("out", 4096)
            max_tokens = options.get("max_tokens", model_settings.get("max_tokens", max_output_tokens))
            max_completion_tokens = options.get("max_completion_tokens", model.settings.get("max_completion_tokens", max_tokens))

            if model_settings.get("max_completion_tokens"):
                max_tokens = NOT_GIVEN
            else:
                max_completion_tokens = NOT_GIVEN

            response = client.chat.completions.create(
                model=model.model,
                messages=thread,
                max_completion_tokens=max_completion_tokens,
                max_tokens=max_tokens,
                response_format=response_format
            )
            self.log_openai_completion_response(response, show=show)

            return response



    def inference_model(self, task: str) -> Optional[Model]:
        model = None
        if task == 'query':
            model = self.settings.inference.models.get(self.args.model_query or self.args.model)
        if task == 'pipe':
            model = self.settings.inference.models.get(self.args.model_pipe or self.args.model)
        if task == 'interactive':
            model = self.settings.inference.models.get(self.args.model_interactive or self.args.model)
        if task == 'edit':
            model = self.settings.inference.models.get(self.args.model_edit or self.args.model)
        if task == 'review':
            model = self.settings.inference.models.get(self.args.model_review or self.args.model)

        if model:
            return model

        l = self.settings.inference.model_picker.get(task) or self.settings.inference.model_picker.get('default') or []
        for key in l:
            if key in self.settings.inference.models:
                return self.settings.inference.models[key]
        return None

    def query_plan(self, query: str) -> Optional[Tuple[bool, dict]]:
        self.log_mode("Query Plan", show=self.args.verbose >= 1)
        planner = self.inference_model("query")
        response = self.run(
            model=planner,
            thread=[
                Prompts.conventions(),
                Prompts.ack(),
                Prompts.system_settings(self.settings),
                Prompts.ack(),
                Prompts.select_model(self.settings.inference, request=query),
            ],
            response_format=Prompts.planner_response_format()
        )
        return self.planner_response(response)

    def pipe_plan(self, query: str, pipe: str) -> Optional[Tuple[bool, dict]]:
        self.log_mode("Pipe Plan", show=self.args.verbose >= 1)
        planner = self.inference_model("pipe")
        request = Prompts.pipe_request(query, pipe)

        thread = [
            Prompts.conventions(),
            Prompts.ack(),
            Prompts.system_settings(self.settings),
            Prompts.ack(),
            Prompts.select_model(
                self.settings.inference,
                request=request,
                additional_instructions="This is a pipe input processing request. Unless asked for formatted output assume desired output is to be raw terminal output."
            )
        ]
        response = self.run(
            model=planner,
            thread=thread,
            response_format=Prompts.planner_response_format()
        )
        return self.planner_response(response)




    def query(self, query: str) -> Optional[str]:
        self.log_mode("Query", show=self.args.verbose >= 1)
        plan = self.query_plan(query)
        if plan:
            _, p = plan
            self.log_query_plan(p, show=self.args.verbose >= 2)

            request = textwrap.dedent(
                """
                {request}                
                
                Additional Instructions:
                {instructions}
                """).format(request=query, instructions=p["instructions"])
            model = self.settings.inference.models[p["model"]]
            response = self.run(
                model=model,
                thread=[
                    Prompts.conventions(),
                    Prompts.ack(),
                    Prompts.system_settings(self.settings, include_system=p["include_settings"]),
                    Prompts.ack(),
                    Prompts.query_prompt(request=request)
                ]
            )
            response_body = response.choices[0].message.content
            response_body = Markdown(response_body) if p["format_output"] else response_body
            std_console.print(response_body)

            self.db.save_chat(
                p["title"],
                self.args,
                p,
                [
                    Prompts.message(content=request),
                    {'role': 'assistant', 'content': response.choices[0].message.content}
                ]
            )
            return response.choices[0].message.content
        return None


    def pipe(self, query: str, pipe: str) -> str | None:
        plan = self.pipe_plan(query,pipe)
        if plan:
            _, p = plan
            self.log_pipe_plan(p, show=self.args.verbose >= 2)

            request = textwrap.dedent(
                """            
                {query}
                
                Additional Instructions:
                {instructions}
                --- INPUT ---
                {pipe}
                """
            ).format(
                query=textwrap.dedent(query),
                pipe=pipe,
                instructions=p["instructions"]
            )

            model = self.settings.inference.models[p["model"]]
            response = self.run(
                model=model,
                thread=[
                    Prompts.conventions(),
                    Prompts.ack(),
                    Prompts.system_settings(self.settings, include_system=p["include_settings"]),
                    Prompts.ack(),
                    Prompts.pipe_prompt(),
                    Prompts.ack(),
                    Prompts.message(content=request),
                ]
            )
            response_body = response.choices[0].message.content
            response_body = Markdown(response_body) if p["format_output"] else response_body
            std_console.print(response_body)

            request = textwrap.dedent(
                """
                {request}                

                Additional Instructions:
                {instructions}
                """).format(request=query, instructions=p["instructions"])
            self.db.save_chat(
                p["title"],
                self.args,
                p,
                [
                    Prompts.message(content=request),
                    {'role': 'assistant', 'content': response.choices[0].message.content}
                ],
                pipe=pipe
            )
            return response.choices[0].message.content
        return None


    def interactive(self, query: Optional[str] = None, pipe: Optional[str] = None) -> None:
        self.log_mode("Interactive", show=self.args.verbose >= 1)