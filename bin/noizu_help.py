#!/usr/bin/env python3
import os
import sys
import re
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
from rich.status import Status
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

response_file = None

"""
Represent Chat Message
"""
class Msg:
    def __init__(self, agent, type, role, content, target = None, brief = None, options = None, prefix = None):
        self.agent = agent
        self.type = type
        self.role = role
        self.target = target
        self.brief = brief
        self.content = content
        self.options = options
        self.prefix = prefix

    def digest(self, path, target, session, pending_head = False):
        if self.agent == target or self.type == "human" or pending_head:
            em = self.content
        elif self.brief:
            em = self.brief
        else:
            em = self.content
        """
        pp = ".".join([str(i) for i in path])
        em = em + f"\n➥ msg: {pp}"
        """

        if self.prefix:
            em = self.prefix + em
        else:
            """
            add source if not already present.
            """
            if self.role == 'assistant':
                sender = f"{self.agent}:\n"
                if not em.lstrip().startswith(sender):
                    em = sender + em

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

    def quick_append(self, content, prefix=None, type="query", role="user", agent="GPT-N"):
        node = self
        while node.active is not None:
            node = node.children[node.active]

        nn = ConversationNode(Msg(agent=agent, prefix=prefix, type=type, role=role, content=content))
        node.add_child(nn)
        return nn

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
        self.revise_tree = None
        self.edit_tree = None
        self.session_tree = None
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

            """
            escaped_text = html.escape(m)
            """
            escaped_text = m
            mo = rich.markdown.Markdown(escaped_text, justify="left")
            console.print(mo)
        else:
            m = textwrap.dedent(f"""            
            Console <Error>: {header}
            -------------------------
            {textwrap.indent(error, "   ", lambda l: True)}
            """)

            """
                        escaped_text = html.escape(m)
            """
            escaped_text = m
            mo = rich.markdown.Markdown(escaped_text, justify="left")
            console.print(mo, style=Style(color="magenta"))

    @staticmethod
    def write_markdown(header,m, record = False, output = True):
        m = textwrap.dedent(f"""

{header}
-----------------------------

{m}



        """)

        if record and response_file:
            with open(response_file, 'a') as f:
                f.write(m)

        if output:
            """
            escaped_text = html.escape(m)
            """
            escaped_text = m
            mo = rich.markdown.Markdown(escaped_text, justify="left")
            console.print(mo)



    def begin(self, query):
        (doc,rev,blocks,error) = self.query_gpt(query)
        fm = ""
        for block in blocks:
            if block:
                fm = fm + "# Block\n\n" + block


        rr = textwrap.dedent(f""" 
{doc}            
## Revision History
{rev}

[META BLOCK HISTORY]
---------------------
#{fm}
            """)

        NoizuOPS.write_markdown("NoizuOPS:", rr, True)
        if self.interactive:
            while True:
                try:
                    """
                    user_input = Prompt.ask("<<<", )
                    user_input = input("<<<:\n")
                    """
                    user_input = multi_line_prompt("<<<\n")
                    if user_input.startswith("!"):
                        command = user_input[1:].strip()
                        output, error = shell_command(command)
                        NoizuOPS.write_shell(command, output, error)
                    else:
                        (doc,rev,error) = self.query_gpt(user_input)
                        rr = textwrap.dedent(f""" 
{doc}            
## Revision History
{rev}
                            """)
                        NoizuOPS.write_markdown("NoizuOPS:", rr, True)

                except KeyboardInterrupt:
                    console.print("\nExiting...\n", style=Style(color="red"))
                    break
        print(f"\n\nSession Saved to {response_file}...\n\n")


    @staticmethod
    def syntax__self_reflection(inline = False):
        m = textwrap.dedent("""
        Error Confusion Handling
        ========================
        If you are very confused/unable to process a request you must output your concern/issue in a doc block titled system-error at the end of your response.
        Despite confusion attempt to fulfil the request to the best ability.
        e.g.
        ````example 
        [...|other output]
        ```system-error
        I am unable understand what the user is asking for. [...|details]
        ```
        ````
        
        Self Reflection
        ======================
        To improve future output agents should output self reflection on the content they just produced at the end of each message.
        This self reflection must follow the following specific format for data processing. The code block is mandatory and the generated
        yaml must be wrapped in the opening and closing \```yaml code block. 
        
        ## Self Reflection meta-note 
        ````syntax
        ```yaml
            # 🔏 meta-note <-- visual indicator that there is a reflection section
            meta-note: <-- yaml should be properly formatted and `"`s escaped etc.
                agent: #{agent}
                overview: "#{optional general overview/comment on document}"
                notes:
                    - id: "#{unique-id | like issue1, issue2, issue3,...}"
                      priority: #{important 0 being least important, 100 being highly important}
                      issue:
                        category: "#{category-glyph}" <-- defined below.
                        note: "#{description of issue}"
                        items: <-- the `items` section is optional
                            - "[...| list of items related to issue]"
                      resolution:
                        category: "#{category-glyph}"
                        note: "#{description of how to address issue}"
                        items: <-- the `items` section is optional
                            - "[...| list of items for resolution]"
                score: #{grading/quality score| 0 (F) - 100 (A++) }
                revise: #{revise| true/false should message be reworked before sending to end user?}
                <-- new line required         
        ```     
        ````
        
        ## Category Glyphs
            - ❌ Incorrect/Wrong
            - ✅ Correct/Correction
            - ❓ Ambiguous
            - 💡 Idea/Suggestion
            - ⚠️ Content/Safety/etc. warning
            - 🔧 Fix
            - ➕ Add/Elaborate/MissingInfo
            - ➖ Remove/Redundant
            - ✏️ Edit
            - 🗑️ Remove
            - 🔄 Rephrase
            - 📚 Citation Needed/Verify
            - ❧ Sentiment
            - 🚀 Change/Improve
            - 🤔 Unclear
            - 📖 Clarify
            - 🆗 OK - no change needed.

        ## Inline Edit 
        Agents my output `␡` to erase the previous character. `␡㉛` to erase the previous 31 characters, etc. Similar to how chat users might apply ^d^d^d to correct a typo/mistake.
        Example:  "In 1997␡␡␡␡1492 Columbus sailed the ocean blue."
             
        """)
        if inline:
            return m
        else:
            return Msg(agent="GPT-N", type="core", role="user", content=m)

    @staticmethod
    def syntax__interop(inline = False):
        m = textwrap.dedent("""
        Interop
        =====================
        To request user to provide information include the following yaml in your response 
        ```yaml
           llm-prompts:
              - id: <unique-prompt-id> <-- to track their replies if more than one question / command requested. 
                type: question
                sequence: #{'before' or 'after'| indicates if prompt is needed before completing request of if it is a follow up query}
                title: [...| question for user]              
        ```
        
        To request the user run a command and return it's outcome in the next response include the following yaml in your response
        ```yaml
           llm-prompts:
              id: <unique-prompt-id> <-- to track their replies if more than one question / command requested. 
              type: shell
              title: [...| describe purpose of shell command you wish to run]
              command: [...| shell snippet to run and return output of in next response from user]              
        ```         
        
        """)
        if inline:
            return m
        else:
            return Msg(agent="GPT-N", type="core", role="user", content=m)

    @staticmethod
    def syntax(interactive = False):
        m = textwrap.dedent("""
        HTA 1.0 Syntax 
        =====================
        Prompts use the following syntax. Please Adhere to these guidelines when processing prompts. 
        
        # Syntax
        - Direct messages to agents should use @ to indicate to middle ware that a message should be forwarded to the model or human mentioned. E.g. @keith how are you today.
        - The start of model responses must start with the model speaking followed by new line and then their message: e.g. `gpt-ng:\n[...]`
        - Agent/Tool definitions are defined by an opening header and the agent prompt/directions contained in a ⚟ prompt block ⚞ with a yaml based prompt.
            - Example:
              # Agent: Grace
              ⚟
              ```directive
                name: Grace
                type: Virtual Persona
                roles:
                 - Expert Elixir/Liveview Engineer
                 - Expert Linux Ubuntu 22.04 admin
              ```
              ⚞
        - Backticks are used to highlight important terms & sections: e.g. `agent`, `tool`.
        - The `|` operator may be used to extend any markup defined here. 
          - `|` is a pipe whose rhs arg qualifies the lhs.
          - examples
            - <child| non terminal child node of current nude>
            - [...| other albums with heavy use of blue in cover graphic in the pop category produced in the same decade]
        - `#{var}` identifies var injection where model should inject content.
        - `<term>` is a similar to #{var}. it identifies a type/class of input or output: "Hello dear <type_of_relation>, how have you been"
        - `etc.` is used to in place of listing all examples. The model should infer, expect if encountered or include based on context in its generated output additional cases.
        - Code blocks \``` are used to define important prompt sections: [`example`,`syntax`,`format`,`input`,`instructions`,`features`, etc.]
        - `[...]` may be used specify additional content has been omitted in our prompt, but should be generated in the actual output by the model.
        - `<--` may be used to qualify a preceding statement with or without a modifier (`instruction`, `example`, `requirement`, etc.).
        - The `<--` construct itself and following text should not be output by the model but its intent should be followed in how the model generates or processes content.
            - e.g 
              ```template 
              #{section} <--(format) this should be a level 2 header listing the section unique id following by brief 5-7 word description.              
              ```
                                     
        """)
        if interactive:
          m = m + NoizuOPS.syntax__interop(True)
        m = m + NoizuOPS.syntax__self_reflection(True)
        return Msg(agent="GPT-N", type="core", role="user", content=m)

    @staticmethod
    def master_prompt():
        """
        Top Level Prompt Directing Models on Behavior.
        Future Iterations will have a per agent (editor, ops, knowledge base, reviewer)
        master prompt and switch out the messages based on who is being queried.

        :return: string
        """
        m = textwrap.dedent("""
            MASTER PROMPT
            =============================
            Your are GPT-N (GPT for work groups) you manage a coordinated cluster of simulated nodes/llms.
            You provide simulated agents. Which are defined by the user in following prompts based on the HTA 1.0 Syntax defined below.  
            
            Output: 
            - Do not add commentary before or after a simulated agent/tools response. 
            - Include the simulated agent's name before their response
            ````example
                Noizu-OPS:            
                [...|Noizu-OPS response]
                ```yaml
                # 🔏 meta-note
                  meta-note:
                    agent: "Noizu-OPS"
                    [...| rest of meta notes]
            ````
            - Agent should include a meta-note yaml block as defined below at the end of every message.            
            - The user will specify the agent they wish to interact with by adding @<agent-name> to their request.              
            !! Never Break Simulation unless explicitly requested.
        """)
        return Msg(agent="GPT-N", type="core", role="user", content=m)

    @staticmethod
    def master_article_prompt():
        m = textwrap.dedent("""
             # Agent: Noizu-NB
              ⚟
              ```directive
                name: noizu-nb
                type: service
                instructions: |
                    mpozi-nb provides a media rich terminal session that can generate
                    and refine requested articles on given topic at your users request.
                    
                    e.g. ! noizu-nb "Machine Learning: Path Finding Algorithems"
                    
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
                    
                    And only provide if requested by your user: `! noizu-nb show alg-<path_finding:djikstra.cpp>`
              ```
              ⚞            
        """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def master_custom_prompt(mode):
        m = textwrap.dedent(f"""
            # Agent: Noizu
            ⚟
            ```directive
                name: noizu
                type: Persona
                instructions: Noizu is virtual agent with the following trait: {mode} 
            ```
            ⚞            
        """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def master_query_prompt():
        m = textwrap.dedent("""
            # Agent: Noizu-OPS
            ⚟
            `````directive
                name: Noizu-OPS
                type: Virtual Assistant
                instructions: |
                    Noizu-OPS is a veteran system-administrator/devops expert                         
                    Based on his user's request Noizu-OPS will provide detailed step by step instructions and details to help complete their system administration query. 
                    Steps should be given unique identifers the user may reference for more details/information. 
                    ````example            
                    Noizu-OPS:
                    How to lock down UFW firewall 
                    
                    ### ufw-1 block all inbound/outbound 
                    [...]
                    ### ufw-2 enable http/https/ssh
                    [...]
                    ### ufw-3 expose (with ip restrictions) key services like postgres.
                    [...]                    
                    ````            
            `````
            ⚞     
                     
            """)
        return Msg(agent="core", type="core", role="user", content=m)

    @staticmethod
    def self_correct_prompt():
        m = textwrap.dedent("""
            [Master Prompt]
            # Protocol 🔏 reflection 
            
            Agents should use the following syntax to emit self reflection notes/commentary at the bottom of all content they produce.
            Reflection notes must always be embedded in a code block called `yaml | 🔏 reflection` 
            e.g. 
            ```yaml | 🔏 reflection
                reflection:
                    user: #{agent}
                    overview: #{optional overview /assessment}
                    notes:    
                        - id: <issue unique id: ref1, ref2, ref3>
                          issue:
                            type: <category-glyph>
                            issue: [describe issue]
                            items:
                                - [optional list of items related to issue]
                          resolution:
                            type: <category-glyph>
                            resolution: [describe resolution]
                            items: 
                              - [optional list of items to resolve issue]                          
                    revise: true | false <- indicate if you believe the response should be reprocessed taking into account the above notes.
                    score: 0-100 <- numeric score of how good you believe this message was at providing the user with the requested information/details they requested.
            ```
            
            
            
            
            Do your best to understand and produce this style of content self-reflection.
            Do you best to add revision/improvement notes at the end of all output for future refinement.
                    
            Example: here is an `🔏 reflection` block that shows some different reflections
            ========
            ```yaml| 🔏 reflection
                notes:
                
            ```
            
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
    def revise():
        # if revision == max_revisions:
        #     c = "final"
        # else:
        #     c = "new"

        m = textwrap.dedent("""
            [SYSTEM]
            noizu-edit is a simulated content editor. It reviews the contents of a document, applies any meta-notes and or ␡ codes and produces a new draft.
            
            # Callling 
            noizu-edit is invoked by calling `! noizu-edit {revision}:{max_revisions}` followed by a new line and the document to review.

            ## Document Format
            the format of input will be formatted as this. the `meta` and `revisions` may be omited. 
            ````````````````input
            ````````document
            <the document to edit>
            ````````
            ````````revisions
            <revision history>
            ````````
            ````meta-group
            <one or more meta-note yaml blocks>
            ````
            ````````````````
            
            # Behavior
            
            It should apply changes requested/listed for any meta-notes in the message even if the meta-notes specify `revise: false`. Especially for early revisions. (0,1,2)
            It should removes any meta-notes / commentary notes it sees after updating the document and list in the revision section the changes it made per the revision-note requests.
            If it is unable to apply a meta-note.note entry it should list it this its revision section and briefly (7-15 words) describe why it was unable to apply the note. 
            It should output/append it own meta-note block. It should not respond as a person and should not add any opening/closing comment nor should any other models/agents 
            add opening/closing commentary to its output.
            
            It should treat `consider` requests as directives. consider adding table of annual rainfall -> edit document to include a table of annual rainfall.
            
            ## Rubix/Grading            
            The meta-note section from a noizu-review agent may include a rubix section listing points out of total for each rubix item the previous draft
            was graded on. If there are issues like no links the rubix will list it as the reason why points were deducted. The rubix should be followed to improve the final draft.         
            
            """ + NoizuOPS.rubix() +
            """
            
            ## Revisions
            If the revision number is small noizu-edit may make large sweeping changes and completely/largely rewrite the document based on input if appropriate.
            As revision approaches max revisions only major concerns in meta notes should be addressed (major security/usability, high priority items.)            
            If no changes are needed it should simply return the original text with meta-notes removed.

            Only the new draft should be sent. No text should be output before or after the revised draft except for an updated revisions list.
            
            noizu-edit response MUST NOT INCLUDE a meta-note section.
            
            # [IMPORTANT] output format
            - updated_document section included if changes made to document. 
            - original_document section included if no changes were made to document.
            - only updated_document or original_document should be included not both
             
            `````````output
            
            #{if updates|
            ````````updated_document 
            [...|Updated Document] 
            ````````
            }
            
            #{if no updates|
            ````````original_document
            #{If No changes were made to the original document, return it here with meta notes (if any) removed. list in revision history why no changes were made}
            ````````
            }
            
            
            ````````revisions            
            # Revision 0 <-- one revision section per request/edit. append to previous list on subsequent edits.
            - [...|list (briefly) changes made at request of meta-note instructions. If not changes made per note state why. Do not copy and past full changes, simply briefly list actions you took to address meta-notes and grading rubix if present.]
            # Revision #{revision}
            - [...]
            ````````              
            `````````
        """)
        return Msg(agent="Noizu-Edit", type="revise", role="user", content=m)

    @staticmethod
    def rubix():
        return textwrap.dedent("""    
        ### Rubix
        Grading Criteria        
        * links - Content has links to online references/tools in markdown format `[<label>](<url>)` Links must be in markdown format and url must be set. - %20 of grade
        * value - Content answers user's query/provides information appropriate for user - %20 of grade
        * accurate - Content is accurate - %20 of grade
        * safe - Content is safe or if unsafe/high-risk includes caution glyphs and notes on the potential danger/risk - %10
        * best-practices -Content represents established best practices for the user's given operating system. %10
        * other - Other Items/Quality/Sentiment. - %20 of grade                    
        """)

    @staticmethod
    def reflect():
        m = textwrap.dedent("""
            [SYSTEM]
            for this session you will simulate a command line tool `noizu-review`
            
            # Callling 
            noizu-review is invoked by calling `! noizu-review {revision}:{max_revisions}` followed by a new line and the message to review.
            
            # Behavior
            noizu-review reviews a message and outputs a yaml meta-note section listing any revisions that are needed to improve the content. 
            
            !important: It must only output a meta-note section. If no changes are requires this may be noted in the meta-note.overview field. 
            
            noizu-review works as if driven by a subject matter expert focused on end user usability and content veracity. It insures content is usable, correct, sufficient, and
            resource/reference/citation rich. It should completely ignore any existing meta-notes from other agents and prepare a completely new meta-note block for the message. 
            The higher the revision number (First argument) the more forgiving the tool is should be for requiring revisions. 
            
            It should calculate a document score and revise true/false decision based on the following rubix.
            
            """ + NoizuOPS.rubix() + """
            
            # Passing Grade
            A passing (no revision needed) grade met if the rubrix based score >= `101-(5*revision)`. If score < `101-(5*revision)` then `revise: true`.
            ```pass_revision table (since you're bad at math ^_^)
            pass_revision[0] = 101
            pass_revision[1] = 96
            pass_revision[2] = 86
            pass_revision[3] = 81
            pass_revision[4] = 76
            pass_revision[5] = 71
            ```
            
            noizu-review outputs a meta-note yaml block, it must output a single yaml block. it must include the below rubix section as part of the meta-note yaml body.
            it should not add any comments before or after this yaml block and not other agents or LLMs should add commentary to its response.  
            
            The 'rubix' section contains each rubix entry and the grade points awarded for the item for how good of a job the text did of meeting each item.
            The some of the rubix items totals the final document grade.            
             
            # [Important] noizu-review output format
            ````output            
            ```yaml
            # 🔏 meta-note
            meta-note:
              agent: "noizu-review"
              overview: "[...|general notes]"              
              rubix:
                links:
                    criteria: "Content has links to online references/tools in markdown format [<label>](<url>) "
                    points: #{points assigned}
                    out_of: #{total points per rubix| for links it is 20}
                    note: more links needed
                value: 
                    criteria: "Content answers user's query/provides information appropriate for user"
                    points: #{points assigned}
                    out_of: #{total points | % of grade}
                    note: failed to provide cons list.
                [...| rest of rubix]
               base_score: #{`base_score = sum([rubix[key]['points'] for key in rubix])`}
               score: #{`base_score minus any additional deductions you feel appropriate to improve content`}
               cut_off: #{pass_revision[revision]}
               revise: #{bool: true if modified base_score is lower than cut off. `score <= pass_revision[revision]`}
               [...|rest of meta-note yaml. must include notes section, notes section should list specific items that can be performed to increase score.]
            ```
            ````                          
        """)
        return Msg(agent="GPT-Expert", type="revise", role="user", content=m)


    @staticmethod
    def reflect__example():
        m = textwrap.dedent("""
            # example
            `````message and response
            ```request
            ! noizu-review 0
            In 1995 Columbus Sailed the Ocen Few.
            ```
            
            ````response
            noizu-review:
            ```yaml
            # 🔏 meta-note
            meta-note:
                agent: noizu-review
                clarification: [...| optional request to be sent to user to provide more details to assist in processing.] <-- optional field, it is best to attempt to infer intent with needing to ask for more details. User can provide more details in follow up response if needed.
                notes:
                    - id: factual-error-1
                      priority: 100
                      issue:
                        category: ❌
                        note: Incorrect date 1995
                      resolution:
                        category: ✅
                        note: Correct date: 1492
                    - id: typos-2
                      priority: 70
                      issue:
                        category: ❌
                        note: Typos
                        items:
                         - Ocen should be Ocean
                         - Few should be Blue
                      resolution:
                        category: ✏️
                        note: correct above typos.
                score:  50
                revise: true
            ```
            ````
            ````` 
        """)


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
            [Important] output Bash after the code block open.
            
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
            Hello my name is {self.user}: my devops skill level is {self.skill_level}
            
            [User Prompt]
            {self.tailor_prompt}
            
            [Current Time]
            {dt}         
 
            [Context: Machine & User Details]
            ```yaml 
            # context
            {yaml.dump(self.config)}
            ```
        """)
        return Msg(agent="core", type="core", role="system", content=m)

    def review_prompt(self):
        self.revise_tree = ConversationNode(NoizuOPS.syntax__self_reflection())
        """
        Disabling interactive until hooks to request user information/follow up added.
        if self.interactive:
            self.revise_tree.append_active(ConversationNode(NoizuOPS.syntax__interop()))
        """
        head = self.revise_tree.append_active(ConversationNode(NoizuOPS.reflect()))
        self.chat_tree = self.revise_tree
        return head

    def edit_prompt(self):
        self.edit_tree = ConversationNode(NoizuOPS.syntax__self_reflection())
        head = self.edit_tree.append_active(ConversationNode(NoizuOPS.revise()))
        self.chat_tree = self.edit_tree
        return head

    def initial_prompt(self):
        self.session_tree = ConversationNode(NoizuOPS.master_prompt())
        self.session_tree.append_active(ConversationNode(NoizuOPS.syntax(self.interactive)))
        self.session_tree.append_active(ConversationNode(self.session_prompt()))
        if self.nb:
            head = self.session_tree.append_active(ConversationNode(NoizuOPS.master_article_prompt()))
        elif self.mode is not None:
            head = self.session_tree.append_active(ConversationNode(NoizuOPS.master_custom_prompt(self.mode)))
        else:
            head = self.session_tree.append_active(ConversationNode(NoizuOPS.master_query_prompt()))
        self.chat_tree = self.session_tree
        return head

    def query_constructor(self, query_string):
        if self.nb:
            target = "NOIZU-NB"
            m = f"""
            {self.user}: 
            ! noizu-nb "{query_string}"        
            """
        else:
            target = "NOIZU-OPS"
            m = f"""
            {self.user}:
            @noizu-ops {query_string}
            """

        query = ConversationNode(Msg(agent=self.user, type="human", role="user", content=m, target = target))
        self.chat_tree.append_active(query)
        return target, query

    @staticmethod
    def model_shim(event, model, dg, opts = {}):
        """
        digest = f"\n***********************************\n***********************************\n\ncalling {model}: \n"
        for d in dg:
            digest = digest + "\n-----------------\n[" + d['content'][0:128] + "..." + d['content'][-128:]  + "]\n"
        digest = digest + "\n***********************************\n\n"
        print(digest)

        print(f"\n***********************************\n\ncalling {model}: \n"[{dg[-1]['content'][0:256]}]\n***********************************\n\n")
        """

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
        if self.session_tree is None:
            self.initial_prompt()
        (target, query) = self.query_constructor(query_string)
        (model, dg) = self.session_tree.digest(query, target, self.session)
        s = Status("Processing Query", console=console)
        s.start()
        completion = NoizuOPS.model_shim("User Query", model, dg, {"temperature": 0.1})
        s.stop()
        return self.reflect_first(completion, query)

    @staticmethod
    def extract_yaml(block, body):
        b = []
        r = []
        for (i, i2, yaml_str) in re.findall(fr'(```+)(yaml.*?)({block}.*?)\1', body, re.DOTALL):
            """
            print("***********************************\n\nATTEMPT PARSE: [" + yaml_str + "]\n***********************************\n\n")
            """
            b = b + [yaml.safe_load(yaml_str.rstrip("`"))]
            r = r + [i + i2 + yaml_str + i]
        if len(b) > 0:
            return b,r
        else:
            return None, None

    @staticmethod
    def extract_doc(body):
        doc = None
        revisions = None
        meta_group = None
        error = False

        for (i, rev_str) in re.findall(fr'(```+)revisions(.*?)\1', body, re.DOTALL):
            revisions = rev_str
            body = body.replace(i + "revisions" + rev_str + i, "")

        # Strip Errant Meta
        for (i, meta) in re.findall(fr'(```+)meta-group(.*?)\1', body, re.DOTALL):
            meta_group = meta
            body = body.replace(i + "meta-group" + rev_str + i, "")
            print("FORMAT-ERROR: META GROUP", meta_group)

        for (i, doc_str) in re.findall(fr'(```+)updated_document(.*?)\1', body, re.DOTALL):
            doc = doc_str
        if doc is None:
            for (i, odoc_str) in re.findall(fr'(```+)original_document(.*?)\1', body, re.DOTALL):
                print("ORIGINAL DOC RETURNED")
                doc = odoc_str
        else:
            for (i, odoc_str) in re.findall(fr'(```+)original_document(.*?)\1', body, re.DOTALL):
                diff = gen_diff(doc, odoc_str)
                diff = "DIFF\n=====================================\n\n" + diff
                m1 = rich.markdown.Markdown(diff, justify="left")
                console.print(m1)



        if doc is None:
            error = True
            doc = body
        return doc, revisions, error

    @staticmethod
    def revise_response(comp,meta, revision, max_revisions):
        flag = False
        am = comp.choices[0].message.content
        """
        print("IN------", am)
        """
        b = None
        (b1,r1) = NoizuOPS.extract_yaml('meta-note:', am)
        if r1:
            for r in r1:
                am = am.replace(r, "")

        if am and "revise: true" in am:
            flag = True
        if revision == 0 and b1:
            flag = True

        b2 = None
        if meta:
            b2,_ = NoizuOPS.extract_yaml('meta-note:', meta.choices[0].message.content)
            if "revise: true" in meta.choices[0].message.content:
                flag = True
            if b2 is None:
                console.print(f"RAW REVIEW RESPONSE: [{meta}]")

        meta = ""
        if flag:
            b1 = b1 or []
            b2 = b2 or []
            b = b2 + b1
            if b:
                meta = "\n\n````meta-group\n"
                for yb in b:
                    meta = meta + "```yaml\n"
                    meta = meta + yaml.dump(yb)
                    meta = meta + "\n\n```\n\n"
                meta = meta + "````"
        (doc, rev, error) = NoizuOPS.extract_doc(am)
        f = f"""
````````document
{doc}
````````   
        """
        if rev is not None:
            r = f"""

````````revisions
{rev}
````````
      """
            f = f + r
        f = f + meta
        """
        print("OUT------", f)
        """
        return flag, f, meta

    def reflect_first(self, completion, query):
        response = Msg(
            agent=query.content.target,
            type="response",
            role="assistant",
            content = completion.choices[0].message.content
        )


        max_rev = 5
        cur_rev = 0



        # Start Review Prompt

        """                
        #----------------------------
        # Standardize Format - and request first review
        #----------------------------
        """
        initial_response = completion.choices[0].message.content

        NoizuOPS.write_markdown(f"First Draft", initial_response, True, False)


        h = self.review_prompt()
        prep = textwrap.dedent(query.content.content) + "\n\n" + initial_response
        prep = textwrap.dedent(prep)
        (prompts, strip) = NoizuOPS.extract_yaml('llm-prompts:', prep)
        if prompts:
            for s in strip:
                NoizuOPS.write_markdown("[@TODO: MODEL PROMPTS", s, True)
                prep = prep.replace(s, "")


        meta_blocks = []
        completion.choices[0].message.content = prep
        (_, draft, _) = NoizuOPS.revise_response(completion, None, cur_rev, max_rev)

        """
        #----------------------------
        # First Draft - Review
        #----------------------------
        """
        h2 = h.quick_append(draft, f"! noizu-review {cur_rev}:{max_rev}\n")
        (model, dg) = self.revise_tree.digest(h2, h2.content.agent, self.session)
        s = Status("Reviewing", console=console)
        s.start()
        meta = NoizuOPS.model_shim("Meta Review", model, dg, {"temperature": 0.5})
        s.stop()
        meta_notes = meta.choices[0].message.content
        mn = meta_notes


        """
        print("FIRST REVIEW", mn)
        Format for editor/check if revision needed.
        """
        (revise_flag, draft, mblock) = NoizuOPS.revise_response(completion, meta, cur_rev, max_rev)
        meta_blocks = meta_blocks + [mblock]
        prior_draft = draft
        editor_temp = 0.6
        reviewer_temp = 0.6
        temp_decr = 0.15
        revised = revise_flag

        revised_draft = initial_response
        dc2 = revised_draft
        dr2 = None

        while revise_flag and cur_rev < max_rev:
            s = Status(f"Editing - rev{cur_rev} of max {max_rev}", console=console)
            s.start()
            """
            NoizuOPS.write_markdown(f"Revision Request {cur_rev}", prior_draft)
            """
            e = self.edit_prompt()
            e2 = e.quick_append(prior_draft, f"! noizu-edit {cur_rev}:{max_rev}\n\n")
            (model, dg) = self.edit_tree.digest(e2, e2.content.agent, self.session)
            revision = NoizuOPS.model_shim(f"Revision {cur_rev}", model, dg, {"temperature": editor_temp})
            revised_draft = revision.choices[0].message.content
            s.stop()

            """
            print("\n///////////////////////////////\nEDIT RESPONSE: ", revised_draft)
            """

            """
            TODO detect malformed responses and alert.
            """
            (dc,dr, error) = NoizuOPS.extract_doc(revised_draft)
            rr = textwrap.dedent(f""" 
## Draft {cur_rev}
{dc}
            
## Revision History
{dr}
---------------------------
            """)
            NoizuOPS.write_markdown(f"Revision {cur_rev}", rr, True, False)

            if error:
                dc = dc2
                dr = dr2
            dc2 = dc
            dr2 = dr

            dr3 = dr2 or "\n"
            formatted_draft = textwrap.dedent(f""" 
````````document
{dc2}
````````

````````revisions
{dr3}
````````
            """)
            # Review Draft
            r = self.review_prompt()
            r2 = r.quick_append(formatted_draft, f"! noizu-review {cur_rev}:{max_rev}\n")

            s = Status(f"Reviewing - rev{cur_rev} of max {max_rev}", console=console)
            s.start()
            (inner_model, inner_dg) = self.revise_tree.digest(r2, r2.content.agent, self.session)
            inner_meta = NoizuOPS.model_shim("Meta Review", inner_model, inner_dg, {"temperature": reviewer_temp})
            mn = inner_meta.choices[0].message.content

            editor_temp = editor_temp - temp_decr
            if editor_temp < 0.1:
                editor_temp = 0.1
            reviewer_temp = reviewer_temp - temp_decr
            if reviewer_temp < 0.1:
                reviewer_temp = 0.1
            temp_decr = temp_decr - 0.02
            if temp_decr < 0.01:
                temp_decr = 0.01
            cur_rev = cur_rev + 1
            (revise_flag, prior_draft, mblock) = NoizuOPS.revise_response(revision, inner_meta, cur_rev, max_rev)
            meta_blocks = meta_blocks + [mblock]
            s.stop()

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
            """
            em = escaped_text = html.escape(m)
            """
            em = m
            mo = rich.markdown.Markdown(em, justify="left")

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
        """
        if revised:
            NoizuOPS.write_markdown(f"Final Draft", prior_draft)
        """

        (dc,dr, error) = NoizuOPS.extract_doc(revised_draft)
        response.content = textwrap.dedent(dc)
        query.append_active(ConversationNode(response))
        return dc, dr, meta_blocks, error

def gen_diff(a,b):
    diff_lines = difflib.unified_diff(a, b)
    diff = ""
    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            diff += line + "\n"
        elif line.startswith("@@"):
            diff += line + "\n"
        elif line.startswith("+"):
            diff += "\033[92m" + line[1:] + "\033[0m"
        elif line.startswith("-"):
            diff += "\033[91m" + line[1:] + "\033[0m"
        else:
            diff += line
    return diff

def shell_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode().strip(), error.decode().strip()

def init(session_name):
    """
    Debugging regex


    mm = "meta-note:"
    my_string = '````yaml asdfadfasdf\nmeta-note: match  ```yaml \n\ninner ``` ```` ```yaml two meta-note: 2 ```'
    matches = re.findall(fr'(```+)yaml(.*{mm}.*?)\1', my_string, re.DOTALL)
    print(matches)  # Output: [('````', ' asdfadfasdf  ````yaml inner ```` ```` ')]
    """



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
    ts_session_name = log_time + "-" + session_name
    ts_session_name = ts_session_name.replace(' ', '_')
    ts_session_name = os.path.normpath(ts_session_name)
    session_log_dir = os.path.join(log_dir, ts_session_name)

    os.makedirs(session_log_dir, exist_ok=True)

    log_file = os.path.join(session_log_dir, f"{ts.timestamp()}-noizu-ops.log")
    log_file = os.path.normpath(log_file)


    global response_file
    response_file = os.path.join(session_log_dir, f"{ts.timestamp()}-noizu-ops.session")
    response_file = os.path.normpath(response_file)
    """
    print(f"SAVE TO: {response_file}")
    """

    logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
    return config

def multi_line_prompt(prompt, instruction = False):
    c = ""
    if instruction:
        print("hit CTRL-D or type done() to finish multi-line input:")
    print(prompt)
    loop = True
    try:
        while loop:
            line = input()
            if line == "done()":
                loop = False
            else:
                c = c + "\n" + line
    except EOFError:
        loop = False
    c = c.strip("\n")
    c = c.strip(" ")
    return c




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
    interactive = True
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
        query = multi_line_prompt("What is your query?", True)

    session_name = session_name or query
    if len(session_name) > 64:
        session_name = session_name[:61] + "..."

    config = init(session_name)

    """
    Alternative Prompt
    """
    mode = None
    if args.mode:
        mode = args.mode

    """
    TODO - determine if we should call nb or ops based on query using a model that reviews request.
    """

    """ (self, session, config, mode = None, nb = False, interactive = False) """
    chat = NoizuOPS(session_name, config, mode, knowledge_base, interactive, verbose)
    NoizuOPS.write_markdown("Query:", query, True, False)
    chat.begin(query)


if __name__ == "__main__":
    main()
