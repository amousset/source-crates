all: clean fmt docs/index.html

fmt:
	mdformat --wrap 100 source-crates.md

docs/index.html: source-crates.md
	mkdir -p docs
	pandoc --standalone --metadata=mainfont:sans --metadata=title:"Statically linked third-party code in Rust crates" \
	       --from commonmark_x --to html5 --toc --toc-depth=2 --output $@ $<

clean:
	rm -rf docs
