# Completions for noizu-help
_noizu_help_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local commands=("query" "--session" "help")
    COMPREPLY=( $(compgen -W "${commands[*]}" -- "${cur}") )
}

complete -F _noizu_help_completions noizu-help
