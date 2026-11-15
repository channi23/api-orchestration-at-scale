// Calls the pinned server's Jinja/autoparser and GBNF matcher; never loads a model.
#include "chat.h"
#include "llama-grammar.h"
#include "nlohmann/json.hpp"
#include <iostream>
#include <cstdio>
#include <unistd.h>
using json = nlohmann::ordered_json;
struct diagnostics_capture {
    FILE *file=tmpfile(); int original=dup(2);
    diagnostics_capture() { if (!file || original<0) throw std::runtime_error("Cannot capture converter diagnostics"); fflush(stderr); dup2(fileno(file),2); }
    std::string finish() {
        fflush(stderr); dup2(original,2); close(original); original=-1;
        rewind(file); std::string text; char buf[4096]; size_t n;
        while ((n=fread(buf,1,sizeof(buf),file))) text.append(buf,n);
        fclose(file); file=nullptr; return text;
    }
    ~diagnostics_capture() { if (original>=0) {dup2(original,2);close(original);} if(file) fclose(file); }
};
int main() {
    std::string line, previous_template;
    common_chat_templates_ptr templates;
    while (std::getline(std::cin, line)) {
        diagnostics_capture capture;
        try {
            auto input = json::parse(line);
            std::string tmpl = input.at("chat_template");
            if (!templates || tmpl != previous_template) {
                templates = common_chat_templates_init(nullptr, tmpl);
                previous_template = tmpl;
            }
            common_chat_templates_inputs request;
            request.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK; // pinned server default
            request.enable_thinking = false;
            request.chat_template_kwargs["enable_thinking"] = "false";
            request.json_schema = input.at("schema").dump();
            common_chat_msg message; message.role="user"; message.content="Return one JSON tool call.";
            request.messages.push_back(message);
            auto params = common_chat_templates_apply(templates.get(), request);
            if (params.grammar.empty() || params.grammar.find("%llguidance") != std::string::npos)
                throw std::runtime_error("Expected nonempty GBNF autoparser grammar");
            auto *initial = llama_grammar_init_impl(nullptr, params.grammar.c_str(), "root", false, nullptr, 0, nullptr, 0);
            if (!initial) throw std::runtime_error("GBNF grammar refused");
            // common/sampling.cpp primes the server grammar with this same generation prompt.
            llama_grammar_accept_str(*initial, params.generation_prompt);
            json out={{"compile_ok",true},{"accepts",json::array()},{"legal_prefix",json::array()},
                      {"grammar",params.grammar}};
            for (auto &sample : input.value("samples",json::array())) {
                auto *g=llama_grammar_clone_impl(*initial);
                bool prefix=true, accepted=false;
                try {
                    llama_grammar_accept_str(*g,sample.get<std::string>());
                    for (const auto &stack : llama_grammar_get_stacks(g)) if (stack.empty()) accepted=true;
                } catch (const std::exception &) {prefix=false;}
                out["accepts"].push_back(prefix && accepted);
                out["legal_prefix"].push_back(prefix);
                llama_grammar_free_impl(g);
            }
            llama_grammar_free_impl(initial);
            out["conversion_diagnostics"]=capture.finish();
            std::cout<<out.dump()<<std::endl;
        } catch (const std::exception &e) {
            std::cout<<json({{"compile_ok",false},{"error",e.what()},{"conversion_diagnostics",capture.finish()}}).dump()<<std::endl;
        }
    }
}
