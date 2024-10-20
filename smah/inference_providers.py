import os
import textwrap
import yaml
import json
from openai import OpenAI
from typing import Dict, Optional, Union, Tuple

OpenAI_TIER_5_MODELS = ["o1-preview", "o1-mini"]

class InferenceProviderBase:
    """
    Base class for inference providers.

    Attributes:
        model (str): The model name.
        context (str): The context in which the model operates.
        description (str): A description of the model.
        strengths (str): The strengths of the model.
        weaknesses (str): The weaknesses of the model.
        tags (dict): Additional tags associated with the model.
        opts (dict): Additional options for the model.

    Methods:
        system_settings_prompt(settings):
            Generates a system settings prompt based on the provided settings.

        model_picker_format():
            Returns the format for the model picker.
    """
    def __init__(self,
                 model=None,
                 context=None,
                 description=None,
                 strengths=None,
                 weaknesses=None,
                 tags={},
                 opts={}):
        self.model = model
        self.context = context
        self.strengths = strengths
        self.weaknesses = weaknesses
        self.description = description
        self.tags = tags
        self.opts = opts



    def system_settings_prompt(self, settings):
        """
        Generates a system settings prompt based on the provided settings.

        Args:
            settings: The settings to include in the prompt.

        Returns:
            dict: A dictionary containing the role and content of the prompt.
        """
        # ------ CONTEXT ----
        contents = settings.to_yaml({"stats": True})
        header = textwrap.dedent("""
                               Settings
                               ================
                               Below are details on the current system and user. Review and reply ack.
                               ----
                               """)
        system_prompt = header + "```yaml\n" + yaml.dump({"settings": contents}, sort_keys=False) + "\n```"
        return {
            "role": "user",
            "content": system_prompt
        }

    def model_picker_format(self):
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
                        "pick": {
                            "type": "string",
                        },
                        "reason": {
                            "type": "string",
                        },
                        "include_context": {
                            "type": "boolean",
                        },
                        "include_context_reason": {
                            "type": "string",
                        },
                        "raw_output": {
                            "type": "boolean",
                        },
                        "raw_output_reason": {
                            "type": "string",
                        }
                    },
                    "additionalProperties": False,
                    "required": ["pick", "reason", "include_context", "include_context_reason","raw_output","raw_output_reason"],
                }
            }
        }

    def to_yaml(self):
        """
        Returns the model details in YAML format.

        Returns:
            dict: A dictionary containing the model details.
        """
        return {
            "model": self.model,
            "description": self.description,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "tags": self.tags,
            "opts": self.opts
        }

    def message(self, role="assistant", content="ack"):
        """
        Generates simple text message.

        Args:
            content (str): The content of the acknowledgment message.

        Returns:
            dict: A dictionary containing the role and content of the acknowledgment message.
        """
        return {
            "role": role,
            "content": content
        }

    def ack(self, role="assistant", content="ack"):
        """
        Generates an acknowledgment message with the given content.

        Args:
            content (str): The content of the acknowledgment message.

        Returns:
            dict: A dictionary containing the role and content of the acknowledgment message.
        """
        return self.message(role, content)


class InferenceProvider:
    """
     Manages different inference models and provides methods to select and interact with them.

     This class is designed to optimize the selection and use of various models for different tasks. It includes methods to choose the best model for initial inference, review, and editing tasks based on specific criteria or complexity levels.

     Attributes:
         openai_api_tier (int): The tier of the OpenAI API being used.
         openai_api_key (str): The API key for accessing OpenAI services.
         openai_api_org (str): The organization ID for OpenAI.
         providers (dict): A dictionary of available inference models.

     Methods:
         patch_model(model):
             Adjusts the model based on the API tier and returns the appropriate model.

         models():
             Returns a dictionary of all available models in YAML format.

         picker_model():
             Returns the default model for picking the best model to use.

         primary_model(complexity):
             Selects and returns the primary model for running initial inference based on the given complexity.

         reviewer_model(complexity):
             Selects and returns the reviewer model for reviewing inference results based on the given complexity.

         editor_model(complexity):
             Selects and returns the editor model for editing tasks based on the given complexity.
     """

    def __init__(self,
                 openai_api_tier=None,
                 openai_api_key=None,
                 openai_api_org=None,
                 providers=None):
        self.openai_api_tier = openai_api_tier or int(os.environ.get("SMAH_OPENAI_API_TIER", "1"))
        self.openai_api_key = openai_api_key or os.environ.get("SMAH_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.openai_api_org = openai_api_org or os.environ.get("SMAH_OPENAI_API_ORG") or os.environ.get("OPENAI_API_ORG")

        self.providers = providers or {
            "gpt-4o": InferenceProvider.OpenAI(
                model="gpt-4o",
                description="gpt-4o - multi modal reasoning.",
                strengths="Multimodal",
                weaknesses="Reasoning weaker than gpt-4-turbo",
                tags={
                    "speed": 4,
                    "reasoning": 5,
                    "planning": 5,
                    "image.in": True,
                    "image.out": True,
                    "audio.out": True,
                    "audio.in": True
                }
            ),
            "gpt-4o-mini": InferenceProvider.OpenAI(
                model="gpt-4o-mini",
                description="Gpt4o Mini - fast multi modal reasoning and output",
                strengths="Fast, multi modal",
                weaknesses="Smaller model, poorer reasoning than gpt4o",
                tags={
                    "speed": 5,
                    "reasoning": 3,
                    "planning": 4,
                    "image.in": True,
                    "image.out": True,
                    "audio.out": True,
                    "audio.in": True
                }
            ),
            "gpt-4-turbo": InferenceProvider.OpenAI(
                model="gpt-4-turbo",
                description="Gpt4 Turbo - fast multimodal reasoning",
                strengths="Fast",
                weaknesses="Smaller model, poorer reasoning than gpt4o",
                tags={
                    "speed": 4,
                    "reasoning": 6,
                    "planning": 6,
                    "image.in": True,
                    "image.out": False,
                    "audio.out": False,
                    "audio.in": False
                }
            ),
            "o1-preview": InferenceProvider.OpenAI(
                model="o1-preview",
                description="o1 - cot embedded reasoning",
                strengths="Reasoning",
                weaknesses="Cost, Speed",
                tags={
                    "speed": 2,
                    "reasoning": 8,
                    "planning": 8,
                    "image.in": False,
                    "image.out": False,
                    "audio.out": False,
                    "audio.in": False
                }
            ),
            "o1-mini": InferenceProvider.OpenAI(
                model="o1-mini",
                description="o1-mini- faster cot embedded reasoning",
                strengths="Reasoning",
                weaknesses="Cost, Speed",
                tags={
                    "speed": 4,
                    "reasoning": 6,
                    "planning": 6,
                    "image.in": False,
                    "image.out": False,
                    "audio.out": False,
                    "audio.in": False
                }
            )
        }

    def patch_model(self, model: str) -> Optional['InferenceProviderBase']:
        """
        Adjusts the model based on the API tier and returns the appropriate model.

        This method ensures that calls to unsupported models (preview models) are prevented
        by substituting them with supported models if the API tier is below 5.

        Args:
            model (str): The name of the model to patch.

        Returns:
            Optional[InferenceProviderBase]: The patched model instance or None if the model is not found.
        """
        if model in OpenAI_TIER_5_MODELS and self.openai_api_tier < 5:
            model = "gpt-4o" if model == "o1-preview" else "gpt-4o-mini"
        return self.providers.get(model)

    def models(self):
        """
        Returns a dictionary of all available models in YAML format for prompt sections.

        Returns:
            dict: A dictionary where keys are model names and values are model details in YAML format.
        """
        return {key: model.to_yaml() for key, model in self.providers.items()}

    def picker_model(self):
        """
        Returns the default model for selecting and instructing system on which model to use and why.

        Returns:
            InferenceProviderBase: The default picker model instance.
        """
        return self.patch_model("gpt-4o-mini")

    class OpenAI(InferenceProviderBase):
        """
        Represents an OpenAI inference model provider.

        This class extends the `InferenceProviderBase` and provides additional functionality specific to OpenAI models. It includes methods for generating prompts, selecting models, and interacting with the OpenAI API.

        Attributes:
            api_key (Union[str, Tuple[str, str]]): The API key for accessing OpenAI services.
            api_org (Union[str, Tuple[str, str]]): The organization ID for OpenAI.

        Methods:
            to_yaml() -> dict:
                Returns the model details in YAML format.

            pick(request: dict, settings: 'Settings') -> Optional[Tuple['InferenceProviderBase', str, bool, str, bool, str]]:
                Selects the best model based on the request and settings, and returns the model along with selection details.

            pipe(query: str, pipe: str, include_context: bool, settings: 'Settings') -> str:
                Processes a pipe input query and returns the response.

            query(query: dict, include_context: bool, settings: 'Settings') -> str:
                Processes a standard query and returns the response.
        """
        def __init__(self,
                     context=None,
                     model=None,
                     api_key=("env", "SMAH_OPENAI_API_KEY"),
                     api_org=("env", "SMAH_OPENAI_ORG"),
                     description=None,
                     strengths=None,
                     weaknesses=None,
                     tags={},
                     opts={}
                     ):
            super().__init__(
                context = context,
                model = model,
                description = description,
                strengths = strengths,
                weaknesses = weaknesses,
                tags = tags,
                opts = opts
            )
            self.api_key = api_key
            self.api_org = api_org

        def pick(self,
                 request: dict,
                 settings: 'Settings'
                 ) -> (Optional)[Tuple['InferenceProviderBase', str, bool, str, bool, str]]:
            """
            Selects the best model based on the request and settings, and returns the model along with selection details.

            Args:
                request (dict): The request details for model selection.
                settings (Settings): The settings to use for model selection.

            Returns:
                Optional[Tuple[InferenceProviderBase, str, bool, str, bool, str]]: The selected model and details, or None if no selection is made.
            """
            provider = settings.providers
            models = textwrap.dedent(yaml.dump({"models": provider.models()}))

            system_prompt = textwrap.dedent("""
            # PROMPT
            You are the Model Selector.
            Based on the following list of available models and the forthcoming request, you will select the best model to perform that request.
            Once the request is sent you are to return a json object
            It must contain the keys 
                - pick: string - set to the model name to use 
                - reason: string - with the reasons to use the selected model.
                - include_context: bool - if system details will be necessary for model to properly respond
                - include_context_reason: string - why context is required for model to respond.
                - raw_output: bool - if response should be plain text (true) or markdown stylized (false).
                - raw_output_reason: string - output for user in other pipes for example should be raw, data analysis can be formatted.

            Always prefer the cheapest of the capable enough models unless instructed otherwise. Told in request a smart model is needed.                                    

            ## Models
            {models}

            --- 
            When you are ready, reply ack.            
            """).format(models=models)

            client = OpenAI(
                api_key=provider.openai_api_key,
                organization=provider.openai_api_org
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    self.message(role="user", content=system_prompt),
                    self.ack(),
                    self.system_settings_prompt(settings),
                    self.ack(),
                    request
                ],
                response_format=self.model_picker_format()
            )

            selection = json.loads(response.choices[0].message.content)
            if selection is None:
                return None
            if all(key in selection for key in
                   ["pick", "reason", "include_context", "include_context_reason", "raw_output", "raw_output_reason"]):
                return (
                    provider.providers[selection["pick"]],
                    selection["reason"],
                    selection["include_context"],
                    selection["include_context_reason"],
                    selection["raw_output"],
                    selection["raw_output_reason"]
                )
            return None

        def pipe(self, query, pipe, include_context, settings):
            provider = settings.providers
            # Deal with too large of input chunks etc. here.
            system_prompt = textwrap.dedent("""
                       # PROMPT
                       You are AI assisted Pipe input processor. Users feed in pipe data and you return pipe output.
                       Do not output anything other than expected pipe output. Do not comment on, reflect on etc. your response.
                       
                       ## Example Valid Response: Possibly requested to find specific numbers in pipe

                           12
                           435
                           15134
                           13420414
                       
                       ## Invalid Response: Not ethe unnecessary intro and outro.

                           Sure I can help you with that.
                           
                           12
                           435
                           15134
                           13420414
                           
                           I hope that helps!
                           
                       ----
                       When you are ready, reply ack.            
                       """)

            operator = settings.user.to_yaml() if settings.user else None
            operator = yaml.dump(operator) if operator else None

            instructions = textwrap.dedent("""
            # PROCESSING INSTRUCTIONS
            Your operator
             
            {operator}
            
            has requested you apply the following logic to the following pipe input messages.
            ----
            {query}
            ----
            Reply ack and I will send the first chunk of the pipe input
            """).format(
                operator=operator,
                query=textwrap.dedent(query)
            )


            pipe_data = textwrap.dedent(
                """
                >>> From Pipe
                ----
                {pipe}            
                """).format(pipe=pipe)

            thread = []
            if include_context:
                thread = [
                    self.message(role="user", content=system_prompt),
                    self.ack(),
                    self.system_settings_prompt(settings),
                    self.ack(),
                    self.message(role="user", content=instructions),
                    self.ack(),
                    self.message(role="user", content=pipe_data)
                ]
            else:
                thread = [
                    self.message(role="user", content=system_prompt),
                    self.ack(),
                    self.message(role="user", content=instructions),
                    self.ack(),
                    self.message(role="user", content=pipe_data)
                ]

            client = OpenAI(
                api_key=provider.openai_api_key,
                organization=provider.openai_api_org)

            # hack for breaking api change
            if self.model in ["o1-preview", "o1-mini"]:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=thread,
                    max_completion_tokens=8192
                )
            else:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=thread,
                    max_tokens=4096
                )
            return response.choices[0].message.content

        def query(self, query: str, include_context: bool, settings: 'Settings') -> str:
            """
            Processes a standard query and returns the response.

            Args:
                query (dict): The query details.
                include_context (bool): Whether to include system context in the query.
                settings (Settings): The settings to use for the query.

            Returns:
                str: The response from the model.
            """
            provider = settings.providers
            system_prompt = textwrap.dedent("""
                # PROMPT
                You are an in-terminal AI Assistant.
                You are to be helpful and take into account your operator's experience levels and details in responding to all requests.

                You are to always use inline reflection/thinking to improve the output of your response. 
                COT improves your performance significantly. 
                
                Use tangents to provide a richer output experience, by connecting loosly related ideas.
                
                Use your inner critique to spot issues/problems and fix them before its too alte. 

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

                Where [...] is used to indicate expected output that is omitted for brevity in this example.
                Do not wrap your entire response in a code fence unless requested.

                ----
                When you are ready, reply ack.
            """)

            operator = settings.user.to_yaml() if settings.user else None
            operator = yaml.dump(operator) if operator else None

            instructions = textwrap.dedent(
                """
                # PROCESSING INSTRUCTIONS
                Your operator

                {operator}

                has made the following request.
                ----
                {query}
                ----
                Please proceed with your response. 
                Think about how you will tailor your response to their inquiry based 
                on their system, and profile.
                 
                Begin your response with a plan/intention statement.
                `thinking: Remember to use inline thinking to improve quality!`        
                """).format(
                operator=operator,
                query=query
            )

            thread = [
                self.message(role="user", content=system_prompt),
                self.ack(content="`thinking: okay I understand the goal and purpose of thinking comments. I only need to reply ack currently`ack"),
                self.message(role="user", content=instructions),
            ]

            if include_context:
                thread = [
                    self.message(role="user", content=system_prompt),
                    self.ack(content="`thinking: okay I understand the goal and purpose of thinking comments. I only need to reply ack currently`ack"),
                    self.system_settings_prompt(settings),
                    self.ack(),
                    self.message(role="user", content=instructions),
                ]
            else:
                thread = [
                    self.message(role="user", content=system_prompt),
                    self.ack(content="`thinking: okay I understand the goal and purpose of thinking comments. I only need to reply ack currently`ack"),
                    self.message(role="user", content=instructions),
                ]

            client = OpenAI(
                api_key=provider.openai_api_key,
                organization=provider.openai_api_org)
            if self.model in ["o1-preview", "o1-mini"]:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=thread,
                    max_completion_tokens=8192
                )
            else:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=thread,
                    max_tokens=4096
                )

            return response.choices[0].message.content