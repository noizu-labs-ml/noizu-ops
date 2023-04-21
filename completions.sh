# Completions for noizu-ops
_noizu_ops_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local commands=("query" "--session" "help")
    COMPREPLY=( $(compgen -W "${commands[*]}" -- "${cur}") )
}

complete -F _noizu_help_completions noizu-ops
