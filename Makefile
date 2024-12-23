NAME := controls-engineering-in-frc

# Make does not offer a recursive wildcard function, so here's one:
rwildcard=$(wildcard $1$2) $(foreach dir,$(wildcard $1*),$(call rwildcard,$(dir)/,$2))

# C++ files that generate SVG files
CPP := $(filter-out ./bookutil/% ./build/% ./lint/% ./snippets/%,$(call rwildcard,./,*.cpp))
ifeq ($(OS),Windows_NT)
	CPP_EXE := $(addprefix build/,$(CPP:.cpp=.exe))
else
	CPP_EXE := $(addprefix build/,$(CPP:.cpp=))
endif

# Python files that generate SVG files
PY := $(filter-out ./bookutil/% ./build/% ./lint/% ./setup_venv.py ./snippets/%,$(call rwildcard,./,*.py))
PY_STAMP := $(addprefix build/,$(PY:.py=.stamp))

TEX := $(filter-out ./controls-engineering-in-frc-ebook.tex ./controls-engineering-in-frc-printer.tex,$(call rwildcard,./,*.tex))
BIB := $(wildcard *.bib)
EBOOK_IMGS := $(addprefix build/controls-engineering-in-frc-ebook/,$(wildcard imgs/*))
PRINTER_IMGS := $(addprefix build/controls-engineering-in-frc-printer/,$(wildcard imgs/*))
SNIPPETS := $(wildcard snippets/*)

ifeq ($(OS),Windows_NT)
	VENV_PYTHON := ./build/venv/Scripts/python3
	VENV_PIP := ./build/venv/Scripts/pip3
else
	VENV_PYTHON := ./build/venv/bin/python3
	VENV_PIP := ./build/venv/bin/pip3
endif

.PHONY: all
all: ebook

.PHONY: ebook
ebook: $(NAME)-ebook.pdf

.PHONY: printer
printer: $(NAME)-printer.pdf

.PHONY: figures
figures: $(CPP_EXE) $(PY_STAMP)

$(NAME)-ebook.pdf: $(TEX) $(NAME)-ebook.tex $(CPP_EXE) $(PY_STAMP) \
		$(BIB) $(EBOOK_IMGS) $(SNIPPETS) build/commit-date.tex \
		build/commit-year.tex build/commit-hash.tex
	latexmk -interaction=nonstopmode -xelatex -shell-escape $(NAME)-ebook

$(NAME)-printer.pdf: $(TEX) $(NAME)-printer.tex $(CPP_EXE) $(PY_STAMP) \
		$(BIB) $(PRINTER_IMGS) $(SNIPPETS) build/commit-date.tex \
		build/commit-year.tex build/commit-hash.tex
	latexmk -interaction=nonstopmode -xelatex -shell-escape $(NAME)-printer

$(EBOOK_IMGS): build/controls-engineering-in-frc-ebook/%.jpg: %.jpg
	@mkdir -p $(@D)
# 150dpi, 75% quality
# cover: 4032x2016 -> 150dpi * 8.5" x 150dpi * 11" -> 1275x1650
# banners: 4032x2016 -> 150dpi * 8.5" x 150dpi * 4.25" -> 1275x637
	if [ "$<" = "imgs/cover.jpg" ]; then \
		magick "$<" -resize 1275x1650 -quality 75 "$@"; \
	else \
		magick "$<" -resize 1275x637 -quality 75 "$@"; \
	fi

$(PRINTER_IMGS): build/controls-engineering-in-frc-printer/%.jpg: %.jpg
	@mkdir -p $(@D)
# 300dpi, 95% quality
# cover: 4032x2016 -> 300dpi * 8.5" x 300dpi * 11" -> 2550x3300
# banners: 4032x2016 -> 300dpi * 8.5" x 300dpi * 4.25" -> 2550x1275
	if [ "$<" = "imgs/cover.jpg" ]; then \
		magick "$<" -resize 2550x3300 -quality 95 "$@"; \
	else \
		magick "$<" -resize 2550x1275 -quality 95 "$@"; \
	fi

build/commit-date.tex: .git/refs/heads/$(shell git rev-parse --abbrev-ref HEAD) .git/HEAD
	@mkdir -p $(@D)
	git log -1 --pretty="format:%ad" --date="format:%B %-d, %Y" > build/commit-date.tex

build/commit-year.tex: .git/refs/heads/$(shell git rev-parse --abbrev-ref HEAD) .git/HEAD
	@mkdir -p $(@D)
	git log -1 --pretty="format:%ad" --date="format:%Y" > build/commit-year.tex

build/commit-hash.tex: .git/refs/heads/$(shell git rev-parse --abbrev-ref HEAD) .git/HEAD
	@mkdir -p $(@D)
	echo "\href{https://github.com/calcmogul/$(NAME)/commit/`git rev-parse --short HEAD`}{commit `git rev-parse --short HEAD`}" > build/commit-hash.tex

build/venv.stamp:
	@mkdir -p $(@D)
	python3 setup_venv.py
	$(VENV_PIP) install -e ./bookutil
	$(VENV_PIP) install frccontrol==2024.22 sleipnirgroup-jormungandr==0.0.1.dev274 pylint qrcode requests robotpy-wpimath==2025.0.0b3
	@touch $@

$(PY_STAMP): build/%.stamp: %.py build/venv.stamp
	@mkdir -p $(@D)
	cd $(@D) && $(abspath $(VENV_PYTHON)) $(abspath ./$<) --noninteractive
	@touch $@

# Run formatters
.PHONY: format
format:
	# Format .tex
	./lint/format_bibliography.py
	./lint/format_eol.py
	./lint/format_paragraph_breaks.py
	# Format .cpp
	find . -type f -name '*.cpp' -not -path './build/*' -print0 | xargs -0 clang-format -i
	# Format .py
	find . -type f -name '*.py' -not -path './build/*' -print0 | xargs -0 python3 -m autoflake -i
	find . -type f -name '*.py' -not -path './build/*' -print0 | xargs -0 python3 -m black -q

# Run formatters and all .tex linters. The commit metadata files and files
# generated by Python scripts are dependencies because check_tex_includes.py
# will fail if they're missing.
.PHONY: lint_tex
lint_tex: format build/commit-date.tex build/commit-year.tex build/commit-hash.tex $(PY_STAMP)
	./lint/check_filenames.py
	./lint/check_tex_includes.py
	./lint/check_tex_labels.py

# Run formatters and all Python linters.
.PHONY: lint_py
lint_py: format build/venv.stamp
	find . -type f -name '*.py' -not -path './build/*' -print0 | xargs -0 $(abspath ./build/venv/bin/python3) -m pylint -s n

# Run formatters and all linters
.PHONY: lint
lint: lint_tex lint_py
	./lint/check_links.py

.PHONY: clean
clean: clean_tex
	rm -rf build

.PHONY: clean_tex
clean_tex:
	latexmk -xelatex -C
	rm -f build/controls-engineering-in-frc-*/qrcode_*.png
	rm -f controls-engineering-in-frc-*.pdf

.PHONY: upload
upload: upload_ebook upload_printer

.PHONY: upload_ebook
upload_ebook: ebook
	rsync --progress $(NAME)-ebook.pdf file.tavsys.net:/srv/file/control/$(NAME).pdf

.PHONY: upload_printer
upload_printer: printer
	rsync --progress $(NAME)-printer.pdf file.tavsys.net:/srv/file/control/$(NAME)-printer.pdf
