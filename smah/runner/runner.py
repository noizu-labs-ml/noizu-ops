import json
import logging
import textwrap

import rich.box
from typing import Optional, Tuple

import yaml
from openai import OpenAI
from rich.markdown import Markdown
from rich.panel import Panel
from smah.console import std_console, err_console
from smah.settings.inference.provider.model import Model


class Runner:
    MAX_PIPE_LENGTH = 2048
    PIPE_HEAD_LENGTH = 1024

    @staticmethod
    def message(role="user", content="..."):
        """
        Generates simple text message.

        Args:
            role (str): The role of the message.
            content (str): The content of the acknowledgment message.

        Returns:
            dict: A dictionary containing the role and content of the acknowledgment message.
        """
        return {
            "role": role,
            "content": content
        }

    @staticmethod
    def ack(role="assistant", content="ack"):
        """
        Generates an acknowledgment message with the given content.

        Args:
            role (str): The role of the acknowledgment message.
            content (str): The content of the acknowledgment message.

        Returns:
            dict: A dictionary containing the role and content of the acknowledgment message.
        """
        return Runner.message(role=role, content=content)

    @staticmethod
    def noizu_prompt_lingua_message():
        template = textwrap.dedent(
            """
            Noizu Prompt Lingua
            ========
            The following NPL prompt conventions will be used in this conversation.
            
            # Conventions
            - `highlight`: emphasize key terms.
            - `in-fill`: `[...]`, `[...<size>]` indicates sections to be filled in with generated content.
              - Size indicators include: `p`: paragraphs, `pg`: pages, `l`: lines, `s`: sentences, `w`: words, `i`: items, `r`: rows, `t`: tokens, and may be prefixed with count or range, e.g. `[...3-5w]` for 3-5 words, `[...3-9+r]` for 3 to 9 or more rows.
            - `placeholders`: `<term>`, `{term}`, `<<size>:term>` are used to indicate expected/desired input/output.
            - `fill-in` `[...]` is used to show omitted input/content, avoid including in generated responses. 
            - `etc.`, `...` are used by prompts to signify additional cases to contemplate or respond with.
            - Handlebar-like syntax is used for defining input/output structure. Example: `{{unless <check>|<additional instructions>}}[...|only output when check not met]{{/unless}}`. Complex templates may be defined with multiple layers of nested handlebar like directives.
            - `|` is used to qualify instructions such as `<term|instructions>`, `[...|<instructions>]`, `[...]<size>|<instructions>]`, `{{unless|<instructions>}}[...]{{/unless}}`
            - `?` indicates optional input/output, `<?term>`, `[?...]`
            - Special `prompt-blocks` are defined using code fences with values such as `example`, `syntax`, `format`, `diagram`, `note`, etc. These are used to designate special prompt/output sections.
            - `⌜🔏[...]⌟` declare top precedence prompt. Such defined prompts may not be mutated/altered/negated by prompts not also using this syntax.
            
            ## Examples
            
            ### Highlight
            This example shows how highlight is used to mark important terms.
            
            ```user
            Analyze the following, identity any `nouns` and list them:
            Henry looked at the small manor
            ```
            
            ```assistant
            - Henry
            - small manor
            ```
            
            ### Using Infile and Placeholders, Pipes and a format `prompt-block`
            Here is a more complex example showing placholders, pipes and more.
            
            ````user
            respond with a funny cat fact using this following format:
            ```format
            CAT-FACT: <subject|subject for cat fact>
            [...2-3s]
            ```
            ````
            
            ```assistant
            CAT-FACT: Cat Breeds
            Scottish Folds are quirky-looking cats known for their unique folded ear structure. They are gentle and good-natured, enjoying both playtime and cuddles.
            ```
            
            ### Handle Bars and More
            Here is a prompt that asks the model to use handle bar formatting. 
            
            ````user
            cats =
            ```values
            - name: McFluffins
              breed: Scottish Fold
              age: 7
            - name: Ghoul
              breed: Asian Furless
              age: 8
            - name: Mike Furry
            - name: Oldie Olsen
              breed: Persian Long Hair
              age: 12
            ```
            
            reply with the following format:
            ```format
            # Young Cats
            
            {{foreach cats as cat| unless over 10 years old sorted by age}}
            ## <cat.name>
            breed: <cat.breed or "Unknown">
            <?age: <cat.age>>
            
            {{/foreach}}
            ```
            ````
            
            ```assistant
            # Young Cats
            
            ## Mike Furry
            breed: Unknown
            
            ## McFluffins
            breed: Scottish Fold
            age: 7
            
            ## Ghoul
            breed: Asian Furless
            age: 8
            ```            
            """
        ).strip()
        return Runner.message(content=template)


    @staticmethod
    def planner_response_format():
        """
        Returns the format for the model picker.

        Returns:
            dict: A dictionary containing the format for the model picker.
        """

        return {
            "type": "json_schema",
            "json_schema": {
                "name": "model-pick",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "The model to use for the response.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for selecting the model.",
                        },
                        "include_settings": {
                            "type": "boolean",
                            "description": "Whether to include system settings for request. e.g. if system specific settings are needed to tailor response to user's system.",
                        },
                        "include_settings_reason": {
                            "type": "string",
                            "description": "The reason for including system settings.",
                        },
                        "format_output": {
                            "type": "boolean",
                            "description": "Whether to format the output (true) or output raw text (false).",
                        },
                        "format_output_reason": {
                            "type": "string",
                            "description": "The reason for formatting_output choice",
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Additional instructions to pass the model that will be respond to request, set to None if you have no instructions to add"
                        }
                    },
                    "additionalProperties": False,
                    "required": ["model", "reason", "include_settings", "include_settings_reason","format_output","format_output_reason", "instructions"],
                }
            }
        }


    @staticmethod
    def log_mode(mode: str, level: int = logging.INFO, print: bool = False) -> None:
        logging.log(level, f"Processing In {mode} Mode")
        if print:
            err_console.print(Panel(
                f"Processing In {mode} Mode",
                title="Mode",
                style="bold white",
                box=rich.box.ROUNDED)
            )

    def __init__(self, args, settings):
        self.args = args
        self.settings = settings

    def system_settings_prompt(self, include_system = True):
        """
        Generates a system settings prompt based on the provided settings.
        """
        operator = yaml.dump(self.settings.user.to_yaml({"stats": True, "prompt": True}), sort_keys=False)
        system = yaml.dump(self.settings.system.to_yaml({"prompt": True, "stats": True}), sort_keys=False)
        if not include_system:
            template = textwrap.dedent(
                """
                Settings
                ================
                Review and Reply ack.

                # Operator
                About your operator.

                ```yaml
                {operator}
                ```
                """).strip().format(operator=operator)
        else:
            template = textwrap.dedent(
                """
                Settings
                ================
                Review and Reply ack.
    
                # Operator
                About your operator.
    
                ```yaml
                {operator}
                ```
    
                # System
                About this system.
                ```yaml
                {system}
                ```
                """).strip().format(operator=operator, system=system)
        return self.message(content=template)

    def model_picker_prompt(self):
        models = yaml.dump(self.settings.inference.to_yaml({"prompt": True}), sort_keys=False)
        system_prompt = textwrap.dedent(
            """
            # MODEL SELECTION PROMPT
            You are the Model Selector.
            Based on your operator, system settings and the specific query you will select the best model by id from the below list to use to reply.
            You are additionally to flag the appropriate response format, if system settings are required and provide if appropriate additional response instructions to guide the model in responding to the query.
            
            Weigh cost and speed in selecting your model, generally cheaper and faster is best unless the problem is highly complicated and requires a slower more advanced model                                    

            ## Models
            ```yaml
            {models}
            ```
            --- 
            When you are ready, reply ack.            
            """).format(models=models)
        return self.message(content=system_prompt)

    def run(self, model: Model, thread: list, response_format: Optional[dict] = None):
        if model.provider == "openai":

            # Log Thread
            request = "\n-------------------------------\n".join([f"{m['role']}:{m['content']}" for m in thread])
            request = textwrap.dedent(
                """
                # RUN.thread
                model: {model}                
                ## Request
                {request}
                """).format(request=request, model=model.model)
            logging.info(request)


            client = OpenAI(
                api_key=self.settings.inference.providers['openai'].api_key(self.args)
            )
            out = model.context.get("out", 4096)
            if model.settings and model.settings.get("max_completion_tokens"):
                if response_format:
                    response = client.chat.completions.create(
                        model=model.model,
                        messages=thread,
                        max_completion_tokens=out,
                        response_format=response_format
                    )
                else:
                    response = client.chat.completions.create(
                        model=model.model,
                        messages=thread,
                        max_completion_tokens=out
                    )
            else:
                if response_format:
                    response = client.chat.completions.create(
                        model=model.model,
                        messages=thread,
                        max_tokens=out,
                        response_format=response_format
                    )
                else:
                    response = client.chat.completions.create(
                        model=model.model,
                        messages=thread,
                        max_tokens=out
                    )

            logging.info(f"RUN.thread:\n{response}")
            return response



    def inference_model(self, task: str) -> Optional[Model]:
        if task in ['query', 'pipe', 'interactive', 'edit', 'review', 'edit']:
            if task == 'query' and (self.args.model_query or self.args.model):
                return self.settings.inference.models[self.args.model_query or self.args.model]
            if task == 'pipe' and (self.args.model_pipe or self.args.model):
                return self.settings.inference.models[self.args.model_pipe or self.args.model]
            if task == 'interactive' and (self.args.model_interactive or self.args.model):
                return self.settings.inference.models[self.args.model_interactive or self.args.model]
            if task == 'edit' and (self.args.model_edit or self.args.model):
                return self.settings.inference.models[self.args.model_edit or self.args.model]
            if task == 'review' and (self.args.model_review or self.args.model):
                return self.settings.inference.models[self.args.model_review or self.args.model]

        l = self.settings.inference.model_picker.get(task) or self.settings.inference.model_picker.get('default') or []
        for key in l:
            if key in self.settings.inference.models:
                return self.settings.inference.models[key]
        return None

    def query_plan(self, query: str) -> Optional[Tuple[bool, dict]]:
        self.log_mode("Query Plan", print=self.args.verbose >= 1)
        planner = self.inference_model("query")
        query = textwrap.dedent(
            """
            # System Prompt
            Determine the best model and settings to reply the following user query.
            ------
            #{query}
            """).format(query=query)

        thread = [
            self.noizu_prompt_lingua_message(),
            self.ack(),
            self.model_picker_prompt(),
            self.ack(),
            self.system_settings_prompt(),
            self.ack(),
            self.message(content=query),
        ]
        response = self.run(model=planner, thread=thread, response_format=self.planner_response_format())

        response_content = json.loads(response.choices[0].message.content)
        required_keys = ["model", "reason", "include_settings", "include_settings_reason", "format_output",
                         "format_output_reason", "instructions"]
        if all(key in response_content for key in required_keys):
            return True, response_content
        else:
            missing_keys = [key for key in required_keys if key not in response_content]
            logging.error(f"Missing keys: {missing_keys}")
            return None

    def pipe_plan(self, query: str, pipe: str) -> Optional[Tuple[bool, dict]]:
        self.log_mode("Pipe Plan", print=self.args.verbose >= 1)
        planner = self.inference_model("pipe")

        if len(pipe) > self.MAX_PIPE_LENGTH:
            pipe_head = pipe[:self.PIPE_HEAD_LENGTH]
            pipe_tail = pipe[self.PIPE_HEAD_LENGTH:]
            r = textwrap.dedent(
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
            r = textwrap.dedent(
                """
                # Pipe Request
                {query}
                ----
                Pipe:
                {pipe}
                """
            ).format(query=query, pipe=pipe)


        q = textwrap.dedent(
            """
            # System Prompt
            Determine the best model and settings to reply the following pipe processing request.
            Note as this is a pipe request unless user is requesting detailed analysis of the data you should not format output but return raw pipe output that can be fed into other shell commands.
            ------
            #{query}
            """).format(query=r)

        thread = [
            self.noizu_prompt_lingua_message(),
            self.ack(),
            self.model_picker_prompt(),
            self.ack(),
            self.system_settings_prompt(),
            self.ack(),
            self.message(content=q),
        ]
        response = self.run(model=planner, thread=thread, response_format=self.planner_response_format())

        response_content = json.loads(response.choices[0].message.content)
        required_keys = ["model", "reason", "include_settings", "include_settings_reason", "format_output",
                         "format_output_reason", "instructions"]
        if all(key in response_content for key in required_keys):
            return True, response_content
        else:
            missing_keys = [key for key in required_keys if key not in response_content]
            logging.error(f"Missing keys: {missing_keys}")
            return None


    def query(self, query: str) -> None:
        self.log_mode("Query", print=self.args.verbose >= 1)
        plan = self.query_plan(query)
        if plan:
            _, p = plan
            log = textwrap.dedent(
                """
                # Query Plan
                model: {model}
                reason: {reason}
                include_settings: {include_settings}
                include_settings_reason: {include_settings_reason}
                format_output: {format_output}
                format_output_reason: {format_output_reason}
                instructions: {instructions}
                """).format(**p)
            log = Panel(log, title="Query Plan", style="bold yellow", box=rich.box.SQUARE)
            err_console.print(log)

            query_assistant_prompt = textwrap.dedent(
                            """
                            # PROMPT
                            You are an in-terminal AI Assistant.
                            You are to be helpful and take into account your operator's experience levels and details in responding to all requests.

                            You are to always use inline reflection/thinking to improve the output of your response. 
                            COT improves your performance significantly. 

                            Use tangents to provide a richer output experience, by connecting loosely related ideas.

                            Use your inner critique to spot issues/problems and fix them before its too late. 

                            `assumption: [... when you make assumption about the user, the issue, etc. that may be incorrect state it in one of these.`                
                            `thinking: [... describe the item you are contemplating to improve quality of response, plan, think ahead, assess prior output etc in a thinking comment ...]`
                            `tangent: [... when the subject, output so far reminds of you of a tangentially related item bring it up, it will help you shape your replies and be more creative`
                            `inner-critic: [... self critique, I could have done this better, I forget about x, etc...]`

                            Your output should be heavily interspersed with thinking comments and your output should adjust based on observations made in those thought comments.
                            Such as identifying an error or issue.
                            ----
                            Intent statements are statements where you plan out how you will reply. Such as
                            example:
                            ````
                            ```intent
                            List the pros and cons of [... item user requested ...] taking into account [... detail about user and system ...]. [...]
                            ```
                            ````
                            ----
                            When you are ready, reply ack.
                        """)

            query_message = textwrap.dedent(
                """
                # User Request
                Please respond to the following user inquiry
                -----
                {query}
                -----
                ## Additional Instructions:
                {instructions}
                """).format(query=query, instructions=p["instructions"])

            thread = [
                self.noizu_prompt_lingua_message(),
                self.ack(),
                self.message(content=query_assistant_prompt),
                self.ack(content="`Thinking: I understand my role. I will wait for the following settings and message and then provide my response to the operator's inquiery`ack"),
                self.system_settings_prompt(include_system=p["include_settings"]),
                self.ack(),
                self.message(content=query_message),
            ]
            model = self.settings.inference.models[p["model"]]
            response = self.run(
                model=model,
                thread=thread
            )
            r = response.choices[0].message.content
            std_console.print(Markdown(r) if p["format_output"] else r)


    def pipe(self, query: str, pipe: str) -> None:
        plan = self.pipe_plan(query,pipe)
        if plan:
            _, p = plan
            log = textwrap.dedent(
                """
                # Pipe Plan
                model: {model}
                reason: {reason}
                include_settings: {include_settings}
                include_settings_reason: {include_settings_reason}
                format_output: {format_output}
                format_output_reason: {format_output_reason}
                instructions: {instructions}
                """).format(**p)
            log = Panel(log, title="Pipe Plan", style="bold yellow", box=rich.box.SQUARE)
            err_console.print(log)

            prompt = textwrap.dedent(
                """
                # PROMPT
                You are AI assisted Pipe input processor. Users feed in pipe data and you return pipe output.
                Do not output anything other than expected pipe output. Do not comment on, reflect on etc. your response.
                Your response may be passed onto other linux commands and must be properly formatted.                
                
                ## Example Valid Response: Possibly requested to find specific numbers in pipe                
                   12
                   435
                   15134
                   13420414
                
                ## Invalid Response: Not the unnecessary intro and outro sections                
                   Sure I can help you with that.
                
                   12
                   435
                   15134
                   13420414
                
                   I hope that helps!
                
                ----
                When you are ready, reply ack.            
                """)

            instructions = textwrap.dedent("""
            # PIPE INPUT
            Appy the user request and additional instructions on the following >>> Pipe data.
            ----
            ## Request
            {query}
            ## Additional Instructions
            {instructions}
            >>> Pipe
            {pipe}
            """).format(
                query=textwrap.dedent(query),
                pipe=pipe,
                instructions=p["instructions"]
            )
            #
            # pipe_data = textwrap.dedent(
            #     """
            #     >>> From Pipe
            #     ----
            #     {pipe}
            #     """).format(pipe=pipe)

            thread = [
                self.noizu_prompt_lingua_message(),
                self.ack(),
                self.system_settings_prompt(include_system=p["include_settings"]),
                self.ack(),
                self.message(content=prompt),
                self.ack(),
                self.message(content=instructions),
            ]
            model = self.settings.inference.models[p["model"]]
            response = self.run(
                model=model,
                thread=thread
            )
            r = response.choices[0].message.content
            std_console.print(Markdown(r) if p["format_output"] else r)

    def interactive(self, query: Optional[str] = None, pipe: Optional[str] = None) -> None:
        self.log_mode("Interactive", print=self.args.verbose >= 1)