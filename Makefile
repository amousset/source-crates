all: clean fmt docs/index.html

fmt:
	mdformat --wrap 100 README.md

docs/index.html: README.md
	mkdir -p docs
	pandoc --standalone --metadata=mainfont:sans --metadata=title:"Pre-RFC: Statically linked external code in Rust crates" \
	       --from commonmark_x --to html5 --toc --toc-depth=2 --output $@ $<

clean:
	rm -rf docs
