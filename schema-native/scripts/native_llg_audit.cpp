// Model-free byte-token audit linked against the exact static library built into llama-server.
#include "llguidance.h"
#include "nlohmann/json.hpp"
#include <iostream>
#include <string>
#include <vector>
using json = nlohmann::ordered_json;
static size_t tokenize(const void *, const uint8_t *bytes, size_t n, uint32_t *out, size_t cap) {
    for (size_t i=0; i<n && i<cap; ++i) out[i]=bytes[i];
    return n;
}
int main() {
    std::vector<uint32_t> lens(257, 1); lens[256]=0;
    std::vector<uint8_t> bytes(256); for (int i=0;i<256;++i) bytes[i]=i;
    LlgTokenizerInit ti{}; ti.vocab_size=257; ti.tok_eos=256; ti.token_lens=lens.data();
    ti.token_bytes=bytes.data(); ti.tokenize_fn=tokenize;
    char error[4096]{}; auto *tok=llg_new_tokenizer(&ti,error,sizeof(error));
    if (!tok) { std::cerr<<error<<"\n"; return 1; }
    LlgConstraintInit ci; llg_constraint_init_set_defaults(&ci,tok); ci.log_stderr_level=0;
    std::string line;
    while (std::getline(std::cin,line)) {
        try {
            auto in=json::parse(line); std::string grammar="%llguidance {}\nstart: %json "+in["schema"].dump();
            auto *initial=llg_new_matcher(&ci,"lark",grammar.c_str());
            auto *err=llg_matcher_get_error(initial);
            json out={{"compile_ok",err==nullptr},{"accepts",json::array()}};
            if (err) out["error"]=err;
            else for (auto &sample:in.value("samples",json::array())) {
                auto *m=llg_clone_matcher(initial); bool ok=true; std::string text=sample.get<std::string>();
                for (unsigned char ch:text) {
                    if (llg_matcher_compute_mask(m)!=0) {ok=false;break;}
                    auto *mask=llg_matcher_get_mask(m);
                    if (!(mask[ch/32] & (1u<<(ch%32))) || llg_matcher_consume_token(m,ch)!=0) {ok=false;break;}
                }
                out["accepts"].push_back(ok && llg_matcher_is_accepting(m)); llg_free_matcher(m);
            }
            llg_free_matcher(initial); std::cout<<out.dump()<<std::endl;
        } catch (const std::exception &e) { std::cout<<json({{"error",e.what()},{"compile_ok",false}}).dump()<<std::endl; }
    }
    llg_free_tokenizer(tok);
}
