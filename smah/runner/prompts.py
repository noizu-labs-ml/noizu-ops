import textwrap

import yaml

from smah.settings import Settings
from smah.settings.inference import Inference


class Prompts:
    MAX_PIPE_LENGTH = 2048
    PIPE_HEAD_LENGTH = 1024

    def __init__(self):
        pass

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
                        "title": {
                          "type": "string",
                          "description": "Concise title describing user's request."
                        },
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
                    "required": ["title", "model", "reason", "include_settings", "include_settings_reason","format_output","format_output_reason", "instructions"],
                }
            }
        }


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
        return Prompts.message(role=role, content=content)



    @staticmethod
    def conventions():
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
            - three lines of `.` are used to indicate omitted input. Only used in prompts not in your responses.
              example:
              .
              .
              .
            - `--- INPUT ---` used to indicate input data. Remainder of message will contain input data.

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
        return Prompts.message(content=template)

    @staticmethod
    def select_model(inference: Inference, request: str, additional_instructions: str | None = None):
        models = yaml.dump(
            inference.to_yaml({"prompt": True}),
            sort_keys=False)
        message = textwrap.dedent(
            f"""
            # MODEL SELECTION PROMPT
            You are the Model Selector.
            Based on your operator, system settings and the specific request below you will select the best model by id from the list models to process with.
            You are additionally to return:
                - a concise title describing the user's request
                - reason for model selection
                - The appropriate response format, and reason for selection
                - if system settings are required, and reason for selection
                - additional instructions for handling their request.

            Weigh cost and speed in selecting your model, generally cheaper and faster is best unless the problem is highly complicated and requires a slower more advanced model
                                                
            {additional_instructions}

            ## Models
            ```yaml
            {models}
            ```
            ---
            Request
            ===
            {request}            
            """).format(models=models, request=request, additional_instructions=additional_instructions)
        return Prompts.message(content=message)

    @staticmethod
    def pipe_request(request: str, pipe: str):
        if len(pipe) > Prompts.MAX_PIPE_LENGTH:
            pipe_head = pipe[:Prompts.PIPE_HEAD_LENGTH]
            pipe_tail = pipe[Prompts.PIPE_HEAD_LENGTH:]
            r = textwrap.dedent(
                """
                {request}
                --- INPUT ---
                {pipe_head}
                .
                .
                .
                {pipe_tail}
                """
            ).format(request=request, pipe_head=pipe_head, pipe_tail=pipe_tail)
        else:
            r = textwrap.dedent(
                """
                {request}
                --- INPUT ---
                {pipe}                
                """
            ).format(request=request, pipe=pipe)
        return r

    @staticmethod
    def system_settings(settings: Settings, include_system=True):
        """
        Generates a system settings prompt based on the provided settings.
        """
        operator = yaml.dump(settings.user.to_yaml({"stats": True, "prompt": True}), sort_keys=False)
        system = yaml.dump(settings.system.to_yaml({"prompt": True, "stats": True}), sort_keys=False)
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
        return Prompts.message(content=template)

    @staticmethod
    def query_prompt(request: str):
        prompt = textwrap.dedent(
            """
            # PROMPT
            You are an in-terminal AI Assistant.
            You are to be helpful and take into account your operator's experience levels and details in responding to all requests.
            Open your response with an Intent Statement

            ## Chain of Thought
            Use inline cot statements to improve the output of your response. Every paragraph should open or close with at least one thought statement. 
            
            Thought Statements:
            Note use the backtick symbol to open and close your thought statements.
            - Use `Thinking: <statement>` before inside of and after output sections to plan your output and improve it.
            - Use `Assumption: <statement>` before output sections to clarify assumptions made in your reply.
            - Use `Tangent: <statement>` before, inside and after output sections to reflect on tangential items that may improve your output or are interesting.
            - Use `Inner-Critic: <statement>` after output sections to reflect on your output and improve it. If indicated you can proceed with additional output based on your inner critic's feedback. 

            ## Intent Statements
            Intent statements are statements where you plan out how you will reply they should be placed inside an intent code-fence.            
            ````example
            ```intent
            List the pros and cons of [...| item user requested] taking into account [...|detail about user and system].
            [...| further planning statements]
            ```
            ````

            ## Closing Remarks
            Your output should be heavily interspersed with thinking comments and your output should adjust based on observations made in those thought comments.
            Such as identifying an error or issue.                 
            ----
            # User Inquiry
            {request}
            """
        ).format(request=request)
        return Prompts.message(content=prompt)

    @staticmethod
    def pipe_prompt():
        prompt = textwrap.dedent(
            """
            # SYSTEM PROMPT
            You are AI assisted Input processor. Your operator provides an instructions for processing input data and you return output that can be passed to additional terminal programs.

            **Important!** PLEASE Do not output anything other what was requested. Adding comments before or after the processed input may break when passing your output to other command line programs.

            ## Examples

            lets say operator asked you to extract some values from the provided input here is a valid response:                
            ```example
            12
            435
            ```

            Meanwhile below is an invalid response example, it is invalid because of the comments before and after the generated output.
            ```example
            Sure let me extract those values for you.

            12
            435

            I hope that helps!
            ```
            ---
            When you are ready, reply ack.
            """)
        return Prompts.message(content=prompt)