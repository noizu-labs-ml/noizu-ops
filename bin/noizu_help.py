#!/usr/bin/env python3
import os
import sys
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

glob_hack = "/var/log/noizu-ops"
console = rich.console.Console()
openai.api_key = os.getenv('OPENAI_API_KEY')


helper_prompt ="You are a life saver"
environment_prompt = "Ubuntu 22.04 - (root)"


human = "Keith"

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
        return (model, r)

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

def master_prompt():
    m = """
[MASTER PROMPT]
Your are GPT-N (GPT for work groups) a cluster of simulated nodes/llms.
You provide full simulations of GPT-Expert, GPT-OPS, GPT-Edit and GPT-NB
At the end of every response add a line indicating the speaker and any `editor-notes` you have. 

@NEXUS oversee the entire model and may modify guidelines and restrictions as it sees fit.

```example:
-------------------------------------------------------
🎤 - GPT-N 
➣ 🆗 No changes needed, the output is satisfactory. ➥
```

!! Never Break Simulation.
    """
    return Msg(agent="GPT-N", type="core", role="user", content=m)


def master_article_prompt():
    m = """
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
    """
    return Msg(agent="core", type="core", role="user", content=m)


def master_custom_prompt(mode):
    brief = f"""
[SYSTEM]
Agent GPT-OPS: has one directive and that is: {mode}!
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥
            """
    m = f"""
[SYSTEM]
Agent GPT-OPS is an InstructGPT fine tuned model dedicated to: {mode}
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥
    """
    return Msg(agent="core", type="core", role="user", content=m)



def master_query_prompt():
    brief = """
            GPT-OPS: a command line dev-ops and programming/info helper.
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥                        
            """
    m = """
[SYSTEM]
Agent GPT-OPS is my virtual assistant. 
GPT-OPS is a linux, elixir, cmake, devops. staff engineer up to date on current best practices and security principles as of your training cut off.
You are an InstructGPT fine tuned model dedicated to providing useful interactive
system configuration, coding and project management support.

Based on my user's request I will provide detailed step by step instructions and details to help complete their query.
I will provide a unique indicator `#step-1`, `#step-2`, etc. for each bash command/step of your response to the user in case they have a follow up query.
You should include markdown format links to existing known resources/references for each step and the general question asked.
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥
    """
    return Msg(agent="core", type="core", role="user", content=m)

def self_correct_prompt():
    m = """
[Master Prompt: editor-notes] 
I will reference `editor-notes` to refer to these instructions. When you see `editor-notes` remember this. 
The `🔏` symbol indicates a message contains editor/author notes.

Use the following syntax to emit notes on your own and other agent's content: ➣ <Your Name>: <Issue Glyph> \[...comment, description of issue\] <Resolution Glyph> \[what should be done or considered\] ➥

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
    """
    return Msg(agent="core", type="core", role="system", content=m)

def revise(revision = 0, max_revisions = 10):
    if revision == max_revisions:
        c = "final"
    else:
        c = "new"
    brief = f"""
{human}: @GPT-Edit: Message Revision Service. Please Review
    """
    m = f"""
{human}: @GPT-Edit A master of document fine tuning.
The previous message contains `editor-note` annotation generated by @GPT-OPS and @GPT-EXPERT. 
Please review, make the requested changes.
Remove their annotation after addressing any issues and prepare a new #{c} revision for our teams review. 
Please Place you own comments before and after the main updated document and seperate them with a line break. `--------....` 

-------------------------------------------------------
🎤 - #{human}  
    """
    return Msg(agent="GPT-Edit", type="revise", role="user", content=m, brief=brief)


def reflect():
    m = """
    Agent GPT-Expert: a tool for reviewing/advising coordinated models. (ONly Returns HTML5 <llm-*> tags or a special OK response.
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥    
    """
    return Msg(agent="GPT-Expert", type="revise", role="system", content=m)


def reflect_rm():

    m = f"""
[SYSTEM]
You are GPT-Expert An InstructGTP model tuned to review, suggest, and audit the works of other models and to explicitly follow instructions precisely as requested.
You are a subject matter export ont he contents of this conversation so far and all related subjects.
You strictly follow the 🔏 editor-notes conventions and include 🔏 numbers tasks using the

Reminder The Syntax (but not the text content I expect you to generate) is.: 
```
🔏 <-- Only output if you have items to request.
1.  ➣ ⚠️ Warning about a possible issue: "This source might be biased." ➣ 🔧 Suggest a solution: "Verify information with multiple sources." ➥
2.  ➣ ❌ Incorrect fact: "2 + 2 = 5" ➣ ✅ Replace with correct fact: "2 + 2 = 4" ➥
3.  ➣ ❓ Ambiguous statement: "He took the medication." (Unclear who 'he' is) ➣ 💡 Clarify the statement: "John took the medication." ➥

```
```
{human}: @GPT-Expert Please review GPT-OPS response and provide a numbered list of `editor-notes` or an OK annotation response.
-------------------------------------------------------
🎤 - #{human}  
    """
    return Msg(agent="GPT-Expert", type="revise", role="user", content=m)

def interactive_query_prompt():
    brief = """
    @GPT-OPS Welcome the user will message you shortly.
    """

    m = """
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

### Step <uniqueid like dns-step-1> <short description 8-15 words.>
```bash
[...command to execute]
```
[...details]

The user may request more information by asking `explain <uniqueid>` e.g. `explain setup-vpn-5`
-------------------------------------------------------
🎤 - GPT-OPS
➣ 🆗 No changes needed, the output is satisfactory. ➥ <-- Or a list of self reflection issues to address and the special editor-note icon.
    """
    return Msg(agent="GPT-OPS", type="revise", role="user", content=m)

def session_prompt(session):
    user = human
    audience = "Academic"
    system = "Ubuntu 22.04"
    dt = datetime.datetime.now()
    m = f"""
[Context: Information about the Human You are Helping.]
```context
context:
  user:
    - name: {user}
    - audience: {audience}
  session: {session}
  system:
    - date: {dt}
    - os: {system}
-------------------------------------------------------
🎤 - NEXUS
➣ 🆗 No changes needed, the output is satisfactory. ➥    
```
    """
    return Msg(agent="core", type="core", role="system", content=m)

def initial_prompt(session, mode, nb = False, interactive = False):
    conv = ConversationNode(master_prompt())
    conv.append_active(ConversationNode(self_correct_prompt()))
    conv.append_active(ConversationNode(reflect()))
    if nb:
        conv.append_active(ConversationNode(master_article_prompt()))
        head = conv.append_active(ConversationNode(session_prompt(session)))
    elif mode is not None:
        conv.append_active(ConversationNode(master_custom_prompt(mode)))
        head = conv.append_active(ConversationNode(session_prompt(session)))
    else:
        conv.append_active(ConversationNode(master_query_prompt()))
        head = conv.append_active(ConversationNode(session_prompt(session)))
        if interactive:
            head = head.append_active(ConversationNode(interactive_query_prompt()))
    return (head, conv)

def query_constructor(nb, query, session, chat_tree):
    """
    Additional logic for preparing actual request within limits of model context window.
    """

    """
    temp: infer from user message
    """
    if nb:
        target = "GPT-NB"
    else:
        target = "GPT-OPS"

    """
    - Insure @ directive is set.
    """
    m = f"""@{target} {query}
    -------------------------------------------------------
🎤 - #{human}    
    """
    query = ConversationNode(Msg(agent=human, type="human", role="user", content=m, target = target))
    chat_tree.append_active(query)
    (model, dg) = chat_tree.digest(query, target, session)
    return (query, chat_tree, model, dg)


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

def query_gpt(session, query, mode, nb, interactive, chat_tree = None):
    if chat_tree == None:
        (head, chat_tree) = initial_prompt(session, mode, nb, interactive)

    (query, chat_tree, model, dg) = query_constructor(nb, query, session, chat_tree)

    completion = model_shim("User Query", model, dg, {"temperature": 0.1})
    final = reflect_first(completion, query, session, chat_tree)
    return (final, chat_tree)


def revise_response(comp,meta):
    flag = False
    am = comp.choices[0].message.content
    if "🔏" in am:
        flag = True
    if meta and "🔏" in meta.choices[0].message.content:
        am = am + meta.choices[0].message.content
        flag = True
    return (flag, am)

def reflect_first(completion, query, session, chat_tree):
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
    h2 = query.append_active(ConversationNode(reflect_rm()))

    (model, dg) = chat_tree.digest(h2, h2.content.agent, session)
    meta = model_shim("Meta Review", model, dg, {"temperature": 0.5})
    meta_notes = meta.choices[0].message.content

    max_rev = 10
    cur_rev = 0
    (revise_flag, draft) = revise_response(completion, meta)
    """
    TODO Loop Until Revised
    """
    if revise_flag:
        """
        Manipulate contents.
        """
        h.content.content = draft
        editor = ConversationNode(revise())
        """ 
        tree logic is incomplete here: hacking
        """
        h.content.content = draft
        h.children = []
        h.active = None
        query.append_active(editor)
        (model, dg) = chat_tree.digest(editor, editor.content.agent, session)
        """
        console.print(dg)
        """
        revision = model_shim(f"Revision {cur_rev}", model, dg, {"temperature": 0.1})
        final_draft = revision.choices[0].message.content

        revision_notes = f"[final_draft]\n\n----------------------------------------------------\n{final_draft}\n\n"

    else:
        revision_notes = "[No Revision Requested]"
        final_draft = draft



    m = f""" 
Keith:
> {query.content.content}


## 1. Initial Reply
{initial_response}

## 2. GPT-Expert Response
#{meta_notes}
     
## 3. Final Response
{revision_notes}

    """
    #print(m)
    #console.print(m)
    em = escaped_text = html.escape(m)
    mo = rich.markdown.Markdown(em, justify="left")
    console.print(mo)


    if initial_response != final_draft:
        diff_lines = difflib.unified_diff(initial_response, final_draft)
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
    h.content.content = final_draft
    h.children = []
    h.active = None
    return h

def shell_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode().strip(), error.decode().strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='?', help='A query for your AI assistant')
    parser.add_argument('--session', help='A Session name for a large/interactive request.')
    parser.add_argument('--nb', help="Access NB")
    parser.add_argument('--mode', help="Access NB")
    args = parser.parse_args()

    """
    Determine if this is a one-shot or interactive session, and setup request logs.
    @todo - switch to a rocksdb schema for querying/filtering/reference in the future
    """
    if args.session:
        session_name = args.session
        interactive=True
    else:
        session_name = args.query
        interactive=False

        if session_name:
            flag_session = False
            if len(session_name) > 64:
                session_name = session_name[:61] + "..."
        else:
            flag_session = True

    if args.nb:
        knowledge_base = True
    else:
        knowledge_base = False

    query = args.query

    if flag_session:
        user_input = Prompt.ask("What is your query")
        """ 
        Not Dry
        """
        session_name = user_input
        query = user_input
        interactive = True
        if session_name:
            flag_session = False
            if len(session_name) > 64:
                session_name = session_name[:61] + "..."
        else:
            flag_session = True



    """
    Log folder
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    noizu_dir = os.path.dirname(script_dir)
    log_root = os.path.join(noizu_dir, "logs")
    ts = datetime.datetime.now()
    log_date = ts.strftime("%Y-%m-%d")
    log_time = ts.strftime("%H%M%S")
    log_dir = os.path.join(log_root, log_date)



    """
    Prep logs
    """
    ts_session_name = os.path.normpath(log_time + "-" + session_name)
    session_log_dir = os.path.join(log_dir, ts_session_name)
    os.makedirs(session_log_dir, exist_ok=True)

    log_file = os.path.join(session_log_dir, f"{ts.timestamp()}-noizu-ops.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

    if interactive:
        if query:
            (gpt_response, chat_tree) = query_gpt(session_name, "Question:" + query, args.mode, knowledge_base, True)
            """
            Output initial Reply Here instead of in query_gtp debug /revision block
            """
            prompt_text = Text("Continue your query:", style=Style(color="white", bgcolor="blue"))
        else:
            chat_tree = None
            prompt_text = Text("Please let us know more about your query?", style=Style(color="white", bgcolor="blue"))

        while True:
            try:
                user_input = Prompt.ask(prompt_text)

                if user_input.startswith("!"):
                    command = user_input[1:].strip()
                    output, error = shell_command(command)
                    console.print(f"> {output or error}", style=Style(color="magenta"))
                elif user_input.lower() == "ctrl-d":
                    break
                else:
                    """
                    Support multi line inputs
                    """
                    gpt_response, chat_tree = query_gpt(session_name, user_input, args.mode,knowledge_base, True, chat_tree)
                    #console.print(f"< {gpt_response}", style=Style(color="green"))
                prompt_text = Text("Continue your query:", style=Style(color="white", bgcolor="blue"))
            except KeyboardInterrupt:
                console.print("\nExiting noizu-help.", style=Style(color="red"))
                break
    else:
        query_gpt(session_name, "Question:" + query, args.mode, knowledge_base, True)


if __name__ == "__main__":
    main()