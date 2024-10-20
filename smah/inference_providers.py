import os
import textwrap
import yaml
import json
from openai import OpenAI

class InferenceProviderBase:
    def __init__(self,
                 model=None,
                 context=None,
                 description=None,
                 strengths=None,
                 weaknesses=None,
                 tags={},
                 opts={}
                 ):
        self.model = model
        self.context = context
        self.strengths = strengths
        self.weaknesses = weaknesses
        self.description = description
        self.tags = tags
        self.opts = opts


    def system_settings_prompt(self, settings):
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

class InferenceProvider:
    def __init__(self,
                 openai_api_tier=None,
                 openai_api_key=None,
                 openai_api_org=None,
                 providers=None):

        if openai_api_tier is None:
            self.openai_api_tier = int(os.environ.get("SMAH_OPENAI_API_TIER", "1"))
        if openai_api_key is None:
            self.openai_api_key = os.environ.get("SMAH_OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY", None)
        if openai_api_org is None:
            self.openai_api_org = os.environ.get("SMAH_OPENAI_API_ORG", None) or os.environ.get("OPENAI_API_ORG", None)


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


    def patch_model(self, model):
        if model in ["o1-preview", "o1-mini"]:
            if self.openai_api_tier > 4:
                pass
            else:
                if model == "o1-preview":
                    model = "gpt-4o"
                else:
                    model = "gpt-4o-mini"
        else:
            pass
        return self.providers[model] if model in self.providers else None

    def models(self):
        return {key: model.to_yaml() for key, model in self.providers.items()}

    def picker_model(self):
        return self.patch_model("o1-mini")

    def primary_model(self, complexity=0.5):
        model = None
        if complexity > 0.9:
            model = "o1-preview"
        elif complexity > 0.8:
            model = "o1-mini"
        elif complexity > 0.7:
            model = "gpt-4-turbo"
        elif complexity > 0.4:
            model = "gpt-4o"
        else:
            model = "gpt-4o-mini"

        return self.patch_model(model)

    def reviewer_model(self, complexity=0.5):
        model = None
        if complexity > 0.95:
            model = "o1-preview"
        elif complexity > 0.85:
            model = "o1-mini"
        elif complexity > 0.8:
            model = "gpt-4-turbo"
        elif complexity > 0.6:
            model = "gpt-4o"
        else:
            model = "gpt-4o-mini"
        return self.patch_model(model)

    def editor_model(self, complexity=0.5):
        model = None
        if complexity > 0.85:
            model = "gpt-4-turbo"
        elif complexity > 0.7:
            model = "gpt-4o"
        else:
            model = "gpt-4o-mini"
        return self.patch_model(model)



    class OpenAI(InferenceProviderBase):
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
        def to_yaml(self):
            return {
                "model": self.model,
                "description": self.description,
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "tags": self.tags,
                "opts": self.opts
            }

        def pick(self, request, settings):
            provider = settings.providers
            models = textwrap.dedent(yaml.dump({"models": provider.models()}))

            system_prompt = textwrap.dedent(f"""
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
            """)

            system_prompt = {
                "role": "user",
                "content": system_prompt
            }

            ack = {
                "role": "assistant",
                "content": "ack"
            }

            system_details_prompt = self.system_settings_prompt(settings)


            client = OpenAI(api_key=provider.openai_api_key, organization=provider.openai_api_org)

            format = self.model_picker_format()
            response = client.chat.completions.create(
                model=self.model,
                messages = [
                    system_prompt,
                    ack,
                    system_details_prompt,
                    ack,
                    request
                ],
                response_format=format
            )

            selection = json.loads(response.choices[0].message.content)
            if selection is None:
                return None
            if "pick" in selection and "reason" in selection and "include_context" in selection and "include_context_reason" in selection:
                return (
                    provider.providers[selection["pick"]],
                    selection["reason"],
                    selection["include_context"],
                    selection["include_context_reason"],
                    selection["raw_output"],
                    selection["raw_output_reason"]
                )

        def pipe(self, query, pipe, include_context, settings):
            provider = settings.providers
            # Deal with too large of input chunks etc. here.
            system_prompt = textwrap.dedent(f"""
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

            system_prompt = {
                "role": "user",
                "content": system_prompt
            }

            ack = {
                "role": "assistant",
                "content": "ack"
            }

            operator = settings.user.to_yaml() if settings.user is not None else None
            operator = yaml.dump(operator) if operator is not None else None

            instructions = textwrap.dedent(f"""
            # PROCESSING INSTRUCTIONS
            Your operator 
            """)
            instructions += f"{operator}"
            instructions += textwrap.dedent(
                f"""
                has requested you apply the following logic to the following pipe input messages.
                ----
                """)
            instructions += f"{textwrap.dedent(query)}"
            instructions += textwrap.dedent(
                f"""
                ----
                Reply ack and I will send the first chunk of the pipe input
                """)

            instructions = {
                "role": "user",
                "content": instructions
            }

            pipe_data = textwrap.dedent(f"""
            >>> From Pipe
            ----            
            """) + pipe
            pipe_data = {
                "role": "user",
                "content": pipe_data
            }

            thread = []
            if include_context:
                thread = [
                    system_prompt,
                    ack,
                    self.system_settings_prompt(settings),
                    ack,
                    instructions,
                    ack,
                    pipe_data
                ]
            else:
                thread = [
                    system_prompt,
                    ack,
                    instructions,
                    ack,
                    pipe_data
                ]

            client = OpenAI(api_key=provider.openai_api_key, organization=provider.openai_api_org)
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

        def query(self, query, include_context, settings):
            provider = settings.providers
            # Deal with too large of input chunks etc. here.
            system_prompt = textwrap.dedent(f"""
                                   # PROMPT
                                   You are an in terminal AI Assistant.
                                   You are to be helpful and take into account your operator's experience levels and details in responding to all requests.
                                   
                                   You are to always use inline reflection/thinking to improve the output of your response. COT improves you performance significantly.
                                   <!-- Thinking: [... describe the item you are contemplating to improve quality of response, plan, think ahead, assess prior output etc in a thinking comment -->
                                 
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
                                   
                                   Where [...] is used to indicate expected output that is omitted for brevity in htis example.
                                   Do not wrap your entire response in a code fence unless requested. 
                                                                                
                                   ----
                                   When you are ready, reply ack.            
                                   """)

            system_prompt = {
                "role": "user",
                "content": system_prompt
            }

            ack = {
                "role": "assistant",
                "content": "<!-- thinking: okay I understand the goal and purpose of thinking comments. I only need to reply ack currently -->ack"
            }

            pure_ack = {
                "role": "assistant",
                "content": "ack"
            }

            tailor_prompt = {
                "role": "user",
                "content": "Think about how you will tailor your response to upcoming user inquiry based on their system and background and output a response plan/intention statement at the start of your next reply to their upcoming message. just reply ack to this prompt."
            }

            thread = []
            if include_context:
                thread = [
                    system_prompt,
                    ack,
                    self.system_settings_prompt(settings),
                    pure_ack,
                    tailor_prompt,
                    pure_ack,
                    query,
                ]

            else:
                thread = [
                    system_prompt,
                    ack,
                    tailor_prompt,
                    pure_ack,
                    query
                ]

            client = OpenAI(api_key=provider.openai_api_key, organization=provider.openai_api_org)
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

