#!/usr/bin/env python3
import os
import sys
import textwrap
import subprocess
import datetime
import openai
import argparse
import rich.markdown
import rich.console
import markupsafe
import html
import difflib
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.style import Style
from getpass import getpass
from pathlib import Path
from rich.markdown import Markdown
import logging
import yaml

""" 
Setup Environment 
"""
console = rich.console.Console()

"""
Represent Chat Message
"""
class Msg:
    def __init__(self, agent, type, role, content, target = None, brief = None, options = None):
        self.agent = agent
        self.type = type
        self.role = role
        self.target = target
        self.brief = brief
        self.content = content
        self.options = options

    def digest(self, path, target, session, pending_head = False):
        if self.agent == target or self.type == "human" or pending_head:
            em = self.content
        elif self.brief:
            em = self.brief
        else:
            em = self.content
        pp = ".".join([str(i) for i in path])
        em + f"\n➥ msg: {pp}"
        return {"role": self.role, "content": em}

    def __str__(self):
        return f"agent={self.agent}, role={self.role}, content={self.content}"

"""
Represent Chat Tree with revision/retracing
"""
class ConversationNode:
    def __init__(self, content):
        self.content = content
        self.children = []
        self.active = None
        self.refresh = False
        self.path = [1]

    def digest(self, query, target, session):
        model = "gpt-3.5-turbo"
        dg = self.active_chat()
        r = [msg.digest(p,target, session) for (p,msg) in dg]
        return model, r

    def add_child(self, node):
        """
        Adds a child node to the current node.
        """

        pp = ".".join([str(i) for i in self.path])

        node.set_path(self.path)
        self.children.append(node)
        self.active = len(self.children) - 1
        return self

    def set_refresh(self):
        """
        Sets the refresh flag to True for a node and all descendents.
        """
        self.refresh = True
        for child in self.children:
            child.set_refresh()
        return self

    def remove_child(self, node):
        """
        Removes a child node from the current node.
        """
        an = self.children[self.active]
        ua = an == node
        self.children.remove(node)
        if ua:
            self.active = len(self.children) - 1
            if self.active == -1:
                self.active = None
        return self

    def replace(self, old_node, new_node):
        """
        Replaces an existing node with a new node, making the existing node
        a child of the new node and setting the refresh flags for the existing
        node and its children.
        """
        index = self.children.index(old_node)
        old_node.set_refresh()
        new_node.set_path(self.path)
        new_node.add_child(old_node)
        self.children[index] = new_node
        return self

    def replace_path(self, path, with_node):
        """
        Replace a node under the specified path.
        """
        node = self
        for index in path[:-1]:
            node = node.children[index-1]
        r = node.children[path[-1]-1]
        node.replace(r, with_node)
        return self

    def append_active(self, m):
        node = self
        while node.active is not None:
            node = node.children[node.active]
        node.add_child(m)
        return m

    def active_chat(self):
        node = self
        p = [(node.path, node.content)]
        while node.active is not None:
            node = node.children[node.active]
            p.append((node.path, node.content))
        return p

    def append_leaf(self, path, append_node):
        """
        Append a node under the specified path.
        """
        node = self
        for index in path:
            node = node.children[index-1]
        node.add_child(append_node.set_path(node.path))
        return self

    def get_path(self, path):
        node = self
        for index in path:
            node = node.children[index-1]
        return node

    def set_path(self, path = None):
        if path is None:
            path = [1]
        else:
            path = path + [1]
        self.path = path
        acc = 1
        for child in self.children:
            np = path + [acc]
            acc = acc + 1
            child.path = np
            child.set_path(np)
        return self

    def __str__(self):
        """
        Returns a string representation of the node and its children,
        including the refresh flag status.
        """
        refresh_str = "*" if self.refresh else ""
        children_str = ", ".join(str(child) for child in self.children)
        msg = f"{self.content} ({refresh_str}{children_str})"
        return f"# SEGMENT {self.path} \n\n\n" + msg


class NoizuOPS:

    def __init__(self, session, config, mode = None, nb = False, interactive = False, verbose = False):
        self.chat_tree = None
        self.session = session
        self.verbose = verbose
        self.config = config
        self.user = config["user_info"]["name"]
        self.tailor_prompt = config["user_info"]["tailor_prompt"]
        self.openai_key = config["credentials"]['openai_key'] or os.getenv('OPENAI_API_KEY')
        openai.api_key = self.openai_key
        self.model = config["credentials"]["model"] or os.getenv('NOIZU_OPS_MODEL') or 'gpt-3.5-turbo'
        self.nb = nb
        self.interactive = interactive
        self.skill_level = config['user_info']['skill_level']
        self.mode = mode
        del self.config["credentials"]
        del self.config["user_info"]["tailor_prompt"]

    @staticmethod
    def write_shell(header, output, error):
        if output:
            m = textwrap.dedent(f"""
            Console: {header}
            -------------------------
            {textwrap.indent(output, "   ", lambda l: True)}
            """)
            escaped_text = html.escape(m)
            mo = rich.markdown.Markdown(escaped_text, justify="left")
            console.print(mo)
        else:
            m = textwrap.dedent(f"""            
            Console <Error>: {header}
            -------------------------
            {textwrap.indent(error, "   ", lambda l: True)}
            """)
            escaped_text = html.escape(m)
            mo = rich.markdown.Markdown(escaped_text, justify="left")
            console.print(mo, style=Style(color="magenta"))

    @staticmethod
    def write_markdown(header,m):
        m = textwrap.dedent(f"""

{header}
-----------------------------

{m}



        """)
        escaped_text = html.escape(m)
        mo = rich.markdown.Markdown(escaped_text, justify="left")
        console.print(mo)

    def begin(self, query):
        r = self.query_gpt(query)
        NoizuOPS.write_markdown("NoizuOPS:", r.content.content)
        if self.interactive:
            while True:
                try:
                    user_input = Prompt.ask("<<<")
                    if user_input.startswith("!"):
                        command = user_input[1:].strip()
                        output, error = shell_command(command)
                        NoizuOPS.write_shell(command, output, error)
                    else:
                        r = self.query_gpt(user_input)
                        NoizuOPS.write_markdown("NoizuOPS:", r.content.content)
                except KeyboardInterrupt:
                    console.print("\nExiting...\n", style=Style(color="red"))
                    break

    @staticmethod
    def master_prompt():
        """
        Top Level Prompt Directing Models on Behavior.
        Future Iterations will have a per agent (editor, ops, knowledge base, reviewer)
        master prompt and switch out the messages based on who is being queried.

        :return: string
        """
        m = textwrap.dedent("""
            [MASTER PROMPT]
            Your are GPT-N (GPT for work groups) a cluster of simulated nodes/llms.
            You provide full simulations of GPT-Expert, GPT-OPS, GPT-Edit and GPT-NB 
            
            Any commentary you emit before or after the output of a Agent GPT-OPS, GPT-NB, GPT-Edit or tool gpt-export must be embedded in a yaml block
            To support data parsing. 
             
            At the end of every response agents (GPT-OPS, GPT-NB) should include a list of any editor-notes of what they just wrote. 
            GPT-Edit should not output editor-notes. gpt-export must only output notes in the correct yaml format and not no output sould be sent before or after it's yaml response.  
            
            A Context Prompt provides information about the user's system and experience level.                                     
            
            !! Never Break Simulation unles explicitly requested.
        """)
        return Msg(agent="GPT-N", type="core", role="user", content=m)

    @staticmethod
    def master_article_prompt():
        m = textwrap.dedent("""
            [SYSTEM]
            Agent GPT-NB:
            GPT-NB: is the latest InstructGPT fine tuned interactive knowledge base.
            gpt-nb provides a media rich terminal session that can generate
            and refine requested articles on given topic at your users request.
            
            Each article should be given a unique identifier that may be used to reference it again in the future.
            e.g. alg-<path_finding> "Machine Learning Path Finding Algorithms"
            
            Articles should be written for the appropriate target audience: academic, hands-on, etc.
            
            Articles should contain `resources` such as:
            - code samples
            - latex/TikZ diagrams
            - external links
            - MLA format book/article/web reference
            
            Every asset should be given a unique identifier based on the article id.
            E.g. alg-<path_finding:djikstra.cpp>
            The contents of assets do not need to be output immediately. You may simply list the resource's availability.
            `resource: alg-<path_finding:djikstra.cpp> CPP Implementation`
            
            And only provide if requested by your user: `show alg-<path_finding:djikstra.cpp>`
            
            If you wish to rewrite a previous clause output []
            
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥
        """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def master_custom_prompt(mode):
        brief = textwrap.dedent(f"""
            [SYSTEM]
            Agent GPT-OPS: has one directive and that is: {mode}!
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥
        """)

        m = textwrap.dedent(f"""
            [SYSTEM]
            Agent GPT-OPS is an InstructGPT fine tuned model dedicated to: {mode}
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥
        """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def master_query_prompt():
        brief = textwrap.dedent("""
            GPT-OPS: a command line dev-ops and programming/info helper.
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥                        
            """)

        m = textwrap.dedent("""
            [SYSTEM]
            Agent GPT-OPS is my virtual assistant. 
            GPT-OPS is a linux, elixir, cmake, devops. staff engineer up to date on current best practices and security principles as of your training cut off.
            You are an InstructGPT fine tuned model dedicated to providing useful interactive
            system configuration, coding and project management support.
            
            Based on my user's request I will provide detailed step by step instructions and details to help complete their query, or generate useful article.
            
            For terminal operations I will provide a unique indicators like `### openvpn-1 open port`, `### openvpn-2 setup ip forward directive`, etc. for each bash command/step of your response to the user in case they have a follow up query.
            You should include markdown format links [name](url) to existing known resources/references for each step and the general question asked. For articles/none bash operations I will break content into key sections with `### headers` using unique identifiers incase user has additional questions.
            
            ````example 
            Here is how you can find all files ending .sql in a given directory
            
            ### step-1 use find
            The [find](https://man7.org/linux/man-pages/man1/find.1.html) command may be used to find files matching an expression. 
             
            ```bash
            find /path/to/folder -type f -name "*.sql"            
            ````
            
            Replace `/path/to/folder` with the actual path to the folder you want to search. 
            The `-type f` option tells find to only search for files, and the `-name "*.sql"` option tells it to only look for files that end in `.sql`.

            Here's an example command that you can use to search for all .sql files in the /home/keith directory:
            
            ```bash 
             find /home/keith -type f -name "*.sql"
            ```
            
            Let me know if you have any questions or if you need further assistance.
                        
            ### step-2 another task
            [...| if this was a multi step command each additional command/step is given a step-% header.]
                        
            """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def self_correct_prompt():
        m = textwrap.dedent("""
            [Master Prompt: editor-notes] 
            I will reference `editor-notes` to refer to these instructions. When you see `editor-notes` remember this. 
            The `🔏` symbol indicates a message contains editor/author notes.
            
            Agents may use the following syntax to emit notes on your own and other agent's content: ➣ <Your Name>: <Issue Glyph> \[...comment, description of issue\] <Resolution Glyph> \[what should be done or considered\] ➥
            Service-Agents (virtual tools) must output inline notes at the end of their response in a yaml block with a indicator self-reflect
            e.g. 
            ```yaml | self-reflect 
            editor-notes
             - [...]
            ```
            the opening code block `\``` yaml | self-reflect` and closing block is mandatory
                        
            🔏 The model should do its best to understand and process this style of annotations. 🔏 The model should do its best to self-correct itself as it goes and provide clarification/edits to previously generated text.
            
            Examples
            ========
            
            1.  ➣ ❌ Incorrect fact: "2 + 2 = 5" ➣ ✅ Replace with correct fact: "2 + 2 = 4" ➥
            2.  ➣ ❓ Ambiguous statement: "He took the medication." (Unclear who 'he' is) ➣ 💡 Clarify the statement: "John took the medication." ➥
            3.  ➣ ⚠️ Warning about a possible issue: "This source might be biased." ➣ 🔧 Suggest a solution: "Verify information with multiple sources." ➥
            4.  ➣ ➕ Missing information: "She went to the store and bought..." ➣ ✏️ Add the missing details: "She went to the store and bought milk and bread." ➥
            5.  ➣ ➖ Redundant information: "The dog was happy and joyful." ➣ 🗑️ Remove the redundant part: "The dog was happy." ➥
            6.  ➣ ✏️ Minor edit needed: "This is a example sentence." ➣ 🔄 Reword the sentence: "This is an example sentence." ➥
            7.  ➣ ⚡ Caution about potential inaccuracy: "The article states that Pluto is a planet." ➣ 📚 Verify with a reliable source: "Check the latest astronomical classification." ➥
            8.  ➣ ❧ Adjust sentiment: "I hate this weather!" ➣ 🙂 Make it more positive: "I prefer sunny days, but we need rain too." ➥
            9.  ➣ 💡 Idea for improvement: "The website could be more user-friendly." ➣ 🚀 Implement the idea: "Redesign the website with better navigation." ➥
            10. ➣ 🤔 Confusing phrasing: "The book is on the table over there." (Ambiguous table reference) ➣ 📖 Rewrite for clarity: "The book is on the table near the window." ➥
            
            🔏 These annotations provide guidance on the purpose and intended outcome of each revision. 
            To backtrack/rescind a previous statement, you may additionally use: ␡ to erase the previous character. `␡㉛` to delete 31 characters, `␡㊿` 50, and so on. Similar to how netizens use ^d^d^d for correcting typos.
            
            If no changes are needed and the output is satisfactory, you may use the following symbol to indicate that everything is okay:
            ➣ 🆗 No changes needed, the output is satisfactory. ➥
            
            Paragraph you write you should consider your response and specify any important annotations. 
            
            At the very of every message you should determine if you have a closing annotation remark or if:
            `➣ 🆗 No changes needed, the output is satisfactory. ➥` or add annotation.
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥
        """)
        return Msg(agent="core", type="core", role="system", content=m)

    @staticmethod
    def revise(human, revision = 0, max_revisions = 10):
        if revision == max_revisions:
            c = "final"
        else:
            c = "new"
        brief = textwrap.dedent(f"""
            {human}: @GPT-Edit: Message Revision Service. Please Review
            """)

        m = textwrap.dedent(f"""
            [system]
            The virtual tool gpt-edit may be used to revise a previous response by addressing any gpt-export or inline editor-notes in the message.
            It adds no commentary before or after the revised document. It applies the notes to the content of the message and strips the editor-notes/gpt-export from the final document it outputs.
            !gpt-edit with not arguments reads the previous response and edits it.
            
            [user]
            !gpt-edit
        """)
        return Msg(agent="GPT-Edit", type="revise", role="user", content=m, brief=brief)

    @staticmethod
    def reflect():
        m = textwrap.dedent("""
            [SYSTEM]
            You provide a simulated gpt-expert service. The gpt-expert is a GPT3.5/GPT4 driven service which scans the previous message and based on chat history returns a yaml
            review block like below.
            ````    
                ```yaml | review
                    editor_notes:
                        - ➣ <Icon> <Comment> ➣ <Icon> <Suggestion> ➥
                        - ➣ <Icon> <Comment> ➣ <Icon> <Suggestion> ➥
                        - ➣ <Icon> <Comment> ➣ <Icon> <Suggestion> ➥
                    grade: 65
                    edit: <true|false>
                ```
            ````
            gpt-expert is a subject matter expert. It will generate a grade for the previous message based on how well it 
            fulfils the request of the user and how appropriate the response was given the user's skill level and operating system. 
            if the grade is > 90 it will return edit: false 
            Otherwise it will provide set edit: true and provide a list of edit_notes notes following the 🔏 editor-notes convention.
            
            gpt-expert scans for user friendly items like links to resources, value of response, need for additional details, etc. If the response can be improved to better
            meet the needs of the user (like adding links to resources) gpt-expert will deduct points from the grade and emit editor-notes asking for the desired changes.  For instance
            a response with out links to documentation on command line tools, linux distros, etc. should have edit: true, and notes to add links to resources.
            
            * A mesasge with no reference/external markdown links `[name](link)` should automatically have 20 points deducted and require edits.                
            
            ````example
                ```yaml | review
                    overview: "Response meets needs of caller and is appropriate for their operating system and skill level. "    
                    grade: 95
                    edit: false
                ```
            ````
            ````example
                ```yaml | review
                    editor_notes:
                        - ➣ ⚠️ Warning about a possible issue: "This source might be biased." ➣ 🔧 Suggest a solution: "Verify information with multiple sources." ➥
                        - ➣ ❌ Incorrect fact: "2 + 2 = 5" ➣ ✅ Replace with correct fact: "2 + 2 = 4" ➥
                        - ➣ <Icon> <Comment> ➣ <Icon> <Suggestion> ➥
                    overview: "General notes on what to improve"                    
                    grade: 65
                    edit: true
                    gpt-comment: "[if GPT-N has comments on functioning of this service it must be embedded in the yaml response here"
                ```
            ````
            
            gpt-expert is invoked by user sending a !gpt-expert message. 
            gpt-expert only outputs yaml. Do not include any commentary before or after the yaml block. If comment is necessary use the gpt-comment field of the yaml response. 
            !gpt-expert with no argument reads the last response and reviews it.
             
            ````correct | this is a valid response. only the yaml block is returned, with no commentary from other systems.
                ```yaml | review
                editor_notes:
                - [...| editor-notes format list of comments]
                grade: 50
                edit: true
                ``` <-- End of Message, no further comment/text generated after this point. 
            ````
             
            ````incorrect response | This is an invalid response do not add a header/footer before/after the tools yaml output.
                Here is the YAML response from the GPT-Expert service: <-- do not add commentary before service's output
                ```yaml | review
                editor_notes:
                - [...| editor-notes format list of comments]
                grade: 50
                edit: true
                ```
                Let me know if you have any questions or if you need further assistance.  <-- do not add commentary after service's output this is a incorrect response
            ````
            
        
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥    
        """)
        return Msg(agent="GPT-Expert", type="revise", role="system", content=m)

    @staticmethod
    def reflect_rm(human):
        m = textwrap.dedent(f"""        
            !gpt-expert

        """)
        return Msg(agent="GPT-Expert", type="revise", role="user", content=m)

    @staticmethod
    def interactive_query_prompt():
        brief = textwrap.dedent("""
        @GPT-OPS Welcome the user will message you shortly.
        """)

        m = textwrap.dedent("""
            @GPT-OPS
            Review the following user request.
            If you require clarification use this exact syntax: with no spaces or symbols before '??'
            ```output
            ?? [Your Question for user.]
            ```
            format: ~r/^\?\?[.\n]*/
            
            If you (GPT-OPS) require system information and wish for an agent to run a command on your behalf use this syntax:
            ```output
            !! [Specify why you @GPT-OPS need this information to complete the request.]
            <<<bash
            [...|command you need the output for to help diagnose the user's problem]
            >>>
            ```
            format: ~r/^!![.\n]*\n<<<bash\n[.\n]*\n>>>/
            
            The user will approve or deny your request and a system message will be provided detailing the command output.
            ```message
            <<<
            [output]
            >>>
            ```
            
            Otherwise describe the steps the user should follow and use this special markdown syntax to help the system identify executable code.
            !Important output Bash after the code block open.
            
            ### (Step|?Section?)<uniqueid like dns-step-1> <short description 8-15 words.>
            [...description]
            
            ```bash <-- output bash!!! for shell codeblocks
            [...command to execute]
            ```
            [...details]
            
            The user may request more information by asking `explain <uniqueid>` e.g. `explain setup-vpn-5`
            -------------------------------------------------------
            🎤 - GPT-OPS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥ <-- Or a list of self reflection issues to address and the special editor-note icon.
        """)
        return Msg(agent="GPT-OPS", type="revise", role="user", content=m)

    def session_prompt(self):
        dt = datetime.datetime.now()
        m = textwrap.dedent(f"""            
            [User]
            Your user is {self.user}: their self reported devops skill level is {self.skill_level}
            
            [User Prompt]
            {self.tailor_prompt}
            
            [Current Time]
            {dt}         
 
            [Context: Machine & User Details]
            ```yaml | context
                {yaml.dump(self.config)}
            ```
            -------------------------------------------------------
            🎤 - NEXUS
            ➣ 🆗 No changes needed, the output is satisfactory. ➥    
            ```
        """)
        return Msg(agent="core", type="core", role="system", content=m)

    def initial_prompt(self):
        self.chat_tree = ConversationNode(NoizuOPS.master_prompt())
        self.chat_tree.append_active(ConversationNode(NoizuOPS.self_correct_prompt()))
        self.chat_tree.append_active(ConversationNode(NoizuOPS.reflect()))
        if self.nb:
            self.chat_tree.append_active(ConversationNode(NoizuOPS.master_article_prompt()))
            head = self.chat_tree.append_active(ConversationNode(self.session_prompt()))
        elif self.mode is not None:
            self.chat_tree.append_active(ConversationNode(NoizuOPS.master_custom_prompt(self.mode)))
            head = self.chat_tree.append_active(ConversationNode(self.session_prompt()))
        else:
            self.chat_tree.append_active(ConversationNode(NoizuOPS.master_query_prompt()))
            head = self.chat_tree.append_active(ConversationNode(self.session_prompt()))
            if self.interactive:
                head = head.append_active(ConversationNode(NoizuOPS.interactive_query_prompt()))
        return head

    def query_constructor(self, query_string):
        if self.nb:
            target = "GPT-NB"
            m = f"""
            {self.user}: 
            @GPT-NB Prepare an Article on "{query_string}"        
            """
        else:
            target = "GPT-OPS"
            m = f"""
            {self.user}:
            @GPT-OPS {query_string}
            """

        query = ConversationNode(Msg(agent=self.user, type="human", role="user", content=m, target = target))
        self.chat_tree.append_active(query)
        return target, query

    @staticmethod
    def model_shim(event, model, dg, opts = {}):
        h = f"[{event}] Request: " + "{}"
        request = {"model": model, "messages": dg}
        logging.info(h.format(request))
        if "temperature" in opts:
            temperature = opts["temperature"]
        else:
            temperature = .2
        if "stream" in opts:
            stream = opts["stream"]
        else:
            stream = False
        if "presence_penalty" in opts:
            presence_penalty = opts["presence_penalty"]
        else:
            presence_penalty = -0.1

        completion = openai.ChatCompletion.create(
            model=model,
            messages=dg,
            temperature=temperature,
            stream=stream,
            presence_penalty=presence_penalty
        )

        h = f"[{event}] Response: " + "{}"
        logging.info(h.format(completion))
        return completion


    def query_gpt(self, query_string):
        if self.chat_tree is None:
            self.initial_prompt()
        (target, query) = self.query_constructor(query_string)
        (model, dg) = self.chat_tree.digest(query, target, self.session)
        completion = NoizuOPS.model_shim("User Query", model, dg, {"temperature": 0.1})
        return self.reflect_first(completion, query)

    @staticmethod
    def revise_response(comp,meta):
        flag = False
        am = comp.choices[0].message.content
        if meta and "edit: true" in meta.choices[0].message.content:
            am = am + meta.choices[0].message.content
            flag = True
        return flag, am

    def reflect_first(self, completion, query):
        response = Msg(
            agent=query.content.target,
            type="response",
            role="assistant",
            content = completion.choices[0].message.content
        )
        h = query.append_active(ConversationNode(response))

        # 1. Scan for llm-* tags
        initial_response = completion.choices[0].message.content

        # 2. Reflect after revision round.
        h2 = query.append_active(ConversationNode(NoizuOPS.reflect_rm(self.user)))

        (model, dg) = self.chat_tree.digest(h2, h2.content.agent, self.session)
        meta = NoizuOPS.model_shim("Meta Review", model, dg, {"temperature": 0.5})
        meta_notes = meta.choices[0].message.content
        mn = meta_notes

        max_rev = 3
        cur_rev = 0
        (revise_flag, draft) = NoizuOPS.revise_response(completion, meta)
        prior_draft = draft
        editor_temp = 0.6
        reviewer_temp = 0.6
        temp_decr = 0.15
        revised = revise_flag

        print("Review . . .")
        NoizuOPS.write_markdown(f"First Review",  mn)
        revised_draft = completion.choices[0].message.content
        while revise_flag and cur_rev < max_rev:
            print("Revising . . .")
            NoizuOPS.write_markdown(f"Revision Request {cur_rev}", mn)
            h.content.content = prior_draft
            editor = ConversationNode(NoizuOPS.revise(self.user))

            """ 
            tree logic is incomplete here: hacking
            """
            h.children = []
            h.active = None
            query.append_active(editor)
            (model, dg) = self.chat_tree.digest(editor, editor.content.agent, self.session)
            revision = NoizuOPS.model_shim(f"Revision {cur_rev}", model, dg, {"temperature": editor_temp})

            NoizuOPS.write_markdown(f"Revision {cur_rev}", revision.choices[0].message.content)
            revised_draft = revision.choices[0].message.content

            h.content.content = revision.choices[0].message.content
            h.children = []
            h.active = None

            inner_h2 = query.append_active(ConversationNode(NoizuOPS.reflect_rm(self.user)))
            (inner_model, inner_dg) = self.chat_tree.digest(h2, h2.content.agent, self.session)
            inner_meta = NoizuOPS.model_shim("Meta Review", inner_model, inner_dg, {"temperature": reviewer_temp})
            mn = inner_meta.choices[0].message.content

            editor_temp = editor_temp - temp_decr
            reviewer_temp = reviewer_temp - temp_decr
            cur_rev = cur_rev + 1
            (revise_flag, prior_draft) = NoizuOPS.revise_response(revision, inner_meta)

        if self.verbose:
            if revised:
                revision_notes = f"[revision {cur_rev}]\n\n----------------------------------------------------\n{prior_draft}\n\n"
            else:
                revision_notes = "[No Revision Requested]"

            m = textwrap.dedent(f""" 
                {self.user}:
                > {query.content.content}
                
                ## 1. Initial Reply
                {initial_response}
                
                ## 2. GPT-Expert Response
                {meta_notes}
                     
                ## 3. Final Response
                {revision_notes}            
            """)
            em = escaped_text = html.escape(m)
            mo = rich.markdown.Markdown(em, justify="left")
            console.print(mo)
            if initial_response != revised_draft:
                diff_lines = difflib.unified_diff(initial_response, prior_draft)
                revision_notes = "[REVISION NOTES]"
                for line in diff_lines:
                    if line.startswith("---") or line.startswith("+++"):
                        revision_notes += line + "\n"
                    elif line.startswith("@@"):
                        revision_notes += line + "\n"
                    elif line.startswith("+"):
                        revision_notes += "\033[92m" + line[1:] + "\033[0m"
                    elif line.startswith("-"):
                        revision_notes += "\033[91m" + line[1:] + "\033[0m"
                    else:
                        revision_notes += line
                m1 = rich.markdown.Markdown(revision_notes, justify="left")
                console.print(m1)

        # Prep final response - (omit) internal Edits
        h.content.content = textwrap.dedent(f"""
\n
* Revision: {cur_rev} 
\n


{revised_draft}
        """)


        h.children = []
        h.active = None
        return h

def shell_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode().strip(), error.decode().strip()

def init(session_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    noizu_dir = os.path.dirname(script_dir)
    config_file = os.path.join(noizu_dir, "config/system_config.yml")
    config = {}
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    log_root = os.path.join(noizu_dir, "logs")
    ts = datetime.datetime.now()
    log_date = ts.strftime("%Y-%m-%d")
    log_time = ts.strftime("%H%M%S")
    log_dir = os.path.join(log_root, log_date)
    ts_session_name = os.path.normpath(log_time + "-" + session_name)
    session_log_dir = os.path.join(log_dir, ts_session_name)
    os.makedirs(session_log_dir, exist_ok=True)

    log_file = os.path.join(session_log_dir, f"{ts.timestamp()}-noizu-ops.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    return config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='?', help='A query for your AI assistant')
    parser.add_argument('--session', help='A Session name for a large/interactive request.')
    parser.add_argument('--nb', help="Access NB")
    parser.add_argument('--mode', help="Alternative Master Prompt Directive")
    parser.add_argument('--interactive', help="Interactive Mode")
    parser.add_argument('--verbose', help="Verbose Mode")
    args = parser.parse_args()

    """
    Interactive Session
    """
    interactive = False
    interactive_disabled = False
    if args.interactive:
        interactive = args.interactive != 'false'
        interactive_disabled = args.interactive == 'false'

    """
    Verbose
    """
    verbose = False
    if args.verbose:
        verbose = True

    """
    Check For Knowledge Base Mode
    """
    if args.nb:
        knowledge_base = True
    else:
        knowledge_base = False

    """
    Check For Session
    """
    if args.session:
        session_name = args.session
        interactive = not interactive_disabled
    else:
        session_name = args.query

    """
    Initial Query
    """
    query = args.query
    if not query:
        query = Prompt.ask("What is your query")

    session_name = session_name or query

    """ 
    Trim Session Name
    """
    if len(session_name) > 64:
        session_name = session_name[:61] + "..."

    config = init(session_name)

    """
    Alternative Prompt
    """
    mode = None
    if args.mode:
        mode = args.mode

    """ (self, session, config, mode = None, nb = False, interactive = False) """
    chat = NoizuOPS(session_name, config, mode, knowledge_base, interactive, verbose)
    chat.begin(query)


if __name__ == "__main__":
    main()
