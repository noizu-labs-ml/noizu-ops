import rich.box
from rich.console import Console
import textwrap
import yaml
from rich.markdown import Markdown
from rich.panel import Panel

class Runner:
    def __init__(self, args, settings):
        self.args = args
        self.settings = settings

    def query(self, query):
        console = Console()
        picker_model = self.settings.providers.picker_model()
        console.print("--- Query ---")

        operator = self.settings.user.to_yaml() if self.settings.user is not None else None
        operator = yaml.dump(operator) if operator is not None else None

        q = textwrap.dedent(f"""
        # CLI User Request
        Your operator:\n""")
        q += f"{operator}"
        q += textwrap.dedent(f"""         
        has the following inquiry:
        ----        
        """)
        q += textwrap.dedent(query)
        query = {
            "role": "user",
            "content": q
        }

        pick = picker_model.pick(query, self.settings)
        if pick is not None:
            pick_model, pick_reason, include_context, include_context_reason, raw_output, raw_output_reason = pick
            #console.print("Picker Model", picker_model.model)
            #console.print(f"Process Using: {pick_model.model}")
            #console.print(f"Reason: {pick_reason}")
            #console.print(f"include_context: {include_context}")
            #console.print(f"include_context_reason: {include_context_reason}")

            picker_response = textwrap.dedent(f"""
            picker: {picker_model.model}
            selected_model: {pick_model.model}
            reason: {pick_reason}
            include_context: {include_context}
            include_context_reason: {include_context_reason}
            raw_output: {raw_output}
            raw_output_reason: {raw_output_reason}            
            """)
            q = Panel(picker_response, title="Query: Model Picker", style="bold yellow", box=rich.box.SQUARE)
            console.print(q)


            q = Panel(query['content'], title="Query", style="bold white", box=rich.box.ROUNDED)
            console.print(q)
            console.print("\n\n\n")

            response = pick_model.query(query, include_context, self.settings)
            q = Panel("LLM Response Below", title="Response", style="bold yellow", box=rich.box.ROUNDED)
            console.print(q)

            m = Markdown(response)
            console.print(m)


    def pipe(self, query, pipe):
        console = Console()
        picker_model = self.settings.providers.picker_model()

        query = textwrap.dedent(query)
        if len(pipe) > 2048:
            pipe_head = pipe[:1024]
            pipe_tail = pipe[1024:]
            request = textwrap.dedent(
            f"""
            # Pipe Request
            """)
            request += f"{query}"
            request += textwrap.dedent(
            f"""
            ----
            Pipe:
            """)
            request += f"{pipe_head}"
            request += textwrap.dedent(
            f"""
            .
            . (anything may be here, it may not be the same content as in the head or tail of stream)
            .            
            """)
            request += f"{pipe_tail}"

            request = {
                "role": "user",
                "content": request
            }
        else:

            request = textwrap.dedent(
                f"""
                # Pipe Request
                """)
            request += f"{query}"
            request += textwrap.dedent(
                f"""
                ----
                Pipe:
                """)
            request += f"{pipe}"

            request = {
                "role": "user",
                "content": request
            }

        # Select Model
        pick = picker_model.pick(request, self.settings)
        if pick is not None:
            pick_model, pick_reason, include_context, include_context_reason, raw_output, raw_output_reason = pick
            #console.print("--- Pipe ---")
            #console.print("Picker Model", picker_model.model)
            #console.print(f"Process Using: {pick_model.model}")
            #console.print(f"Reason: {pick_reason}")
            #console.print(f"include_context: {include_context}")
            #console.print(f"include_context_reason: {include_context_reason}")

            picker_response = textwrap.dedent(f"""
            picker: {picker_model.model}
            selected_model: {pick_model.model}
            reason: {pick_reason}
            include_context: {include_context}
            include_context_reason: {include_context_reason}
            raw_output: {raw_output}
            raw_output_reason: {raw_output_reason}    
            """)
            q = Panel(picker_response, title="Pipe: Model Picker", style="bold yellow", box=rich.box.SQUARE)
            console.print(q)

            q = Panel(query, title="Query", style="bold white", box=rich.box.ROUNDED)
            console.print(q)




            response = pick_model.pipe(query, pipe, include_context, self.settings)

            q = Panel("LLM Pipe Response", title="Response", style="bold yellow", box=rich.box.ROUNDED)
            console.print(q)

            if raw_output:
                print(response)
            else:
                print(response)
                #m = Markdown(response)
                #console.print(m)

    def interactive(self, pipe=None):
        console = Console()
        picker_model = self.settings.providers.picker_model()
        console.print("--- Interactive ---")
        console.print("Picker Model", picker_model.model)
        console.print("Interactive")
        console.print(f"Pipe: {pipe}")