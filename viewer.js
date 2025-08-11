// viewer.js
const repo = "atras-do-arwario/liberty-knowledge-base";
const branch = "main";
const baseRawUrl = `https://raw.githubusercontent.com/${repo}/${branch}/`;

let sections = [];
let flatSections = [];
let fuseTitles;
let fullMd = "";
let isFullView = false;
let isSearching = false;
let isEnterSearch = false;
let currentPath = "";

async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const path = urlParams.get("file");
    if (!path) {
        alert("No file specified");
        window.location.href = "index.html";
        return;
    }
    currentPath = path;

    try {
        const response = await fetch(baseRawUrl + path);
        if (!response.ok)
            throw new Error(`Failed to fetch ${path}: ${response.status}`);
        const md = await response.text();
        sections = buildSections(md);
        flatSections = flattenSections(sections);
        fuseTitles = new Fuse(flatSections, {
            keys: ["title"],
            includeScore: true,
            threshold: 0.4,
        });
        fullMd = getFullMarkdown(sections);
        document.getElementById("file-title").textContent = path;
        const downloadLink = document.getElementById("download-link");
        downloadLink.href = baseRawUrl + path;
        downloadLink.download = path.split("/").pop();
        renderTOC(sections, document.getElementById("toc-tree"));
        marked.setOptions({
            gfm: true,
            headerIds: true,
            headerPrefix: "",
            highlight: function (code, lang) {
                const language = hljs.getLanguage(lang) ? lang : "plaintext";
                return hljs.highlight(code, { language }).value;
            },
            langPrefix: "hljs language-",
        });
        const query = urlParams.get("q");
        if (query) {
            const searchInput = document.getElementById("content-search");
            searchInput.value = query;
            handleSearch(query);
        }
        handleInitialHash();
    } catch (error) {
        console.error("Error loading file:", error);
        alert("Failed to load file");
        window.location.href = "index.html";
    }

    window.addEventListener("popstate", (event) => {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get("q");
        const searchInput = document.getElementById("content-search");
        searchInput.value = query || "";
        handleSearch(query || "");
        if (event.state && event.state.hash) {
            location.hash = event.state.hash;
            handleInitialHash(); // Re-handle hash on popstate
        }
    });
}

function buildSections(md) {
    const lines = md.split("\n");
    const root = { children: [], level: 0 };
    let stack = [root];
    let buffer = [];
    for (let line of lines) {
        const match = line.match(/^(#{1,6})\s+(.*)/);
        if (match) {
            const level = match[1].length;
            const title = match[2].trim();
            if (buffer.length) {
                stack[stack.length - 1].content = buffer.join("\n").trim();
                buffer = [];
            }
            while (stack.length > level) {
                stack.pop();
            }
            const newSec = {
                title,
                level,
                content: "",
                children: [],
                id: title.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
            };
            stack[stack.length - 1].children.push(newSec);
            stack.push(newSec);
        } else {
            buffer.push(line);
        }
    }
    if (buffer.length) {
        stack[stack.length - 1].content = buffer.join("\n").trim();
    }
    return root.children;
}

function flattenSections(sections) {
    return sections.flatMap((s) => [s, ...flattenSections(s.children)]);
}

function getSectionMarkdown(section) {
    let md = "#".repeat(section.level) + " " + section.title + "\n\n";
    if (section.content) {
        md += section.content + "\n\n";
    }
    for (let child of section.children) {
        md += getSectionMarkdown(child);
    }
    return md.trim() + "\n";
}

function getFullMarkdown(sections) {
    return sections.map((s) => getSectionMarkdown(s)).join("\n");
}

function renderTOC(sections, container) {
    container.innerHTML = "";
    buildTree(sections, container, 1);
}

function buildTree(sections, parentElem, depth) {
    sections.forEach((section) => {
        const details = document.createElement("details");
        details.style.marginLeft = `${(depth - 1) * 1}rem`;
        const summary = document.createElement("summary");
        summary.textContent = section.title;
        summary.id = section.id;

        const copyBtn = document.createElement("button");
        copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy MD';
        copyBtn.className = "copy-btn";
        copyBtn.setAttribute("aria-label", "Copy section markdown");
        copyBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const mdContent = getSectionMarkdown(section);
            navigator.clipboard
                .writeText(mdContent)
                .then(() => {
                    copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied';
                    copyBtn.classList.add("copied");
                    setTimeout(() => {
                        copyBtn.innerHTML =
                            '<i class="fas fa-copy"></i> Copy MD';
                        copyBtn.classList.remove("copied");
                    }, 2000);
                })
                .catch((err) => {
                    console.error("Copy error:", err);
                });
        });
        summary.appendChild(copyBtn);

        details.appendChild(summary);
        const contentDiv = document.createElement("div");
        contentDiv.className = "markdown-body";
        details.appendChild(contentDiv);
        if (section.children.length) {
            const childrenDiv = document.createElement("div");
            buildTree(section.children, childrenDiv, depth + 1);
            details.appendChild(childrenDiv);
        }
        details.addEventListener("toggle", (e) => {
            const det = e.target;
            if (det.open) {
                if (!contentDiv.innerHTML && section.content) {
                    contentDiv.innerHTML = marked.parse(section.content);
                    const footer = document.createElement("div");
                    footer.className = "section-footer";
                    const retractBtn = document.createElement("button");
                    retractBtn.className = "retract-btn";
                    // TODO: maybe having no innerHTML is not recommended.
                    // retractBtn.innerHTML = '<i class="fas fa-chevron-up"></i>'; // used pico css chevron
                    retractBtn.setAttribute(
                        "aria-label",
                        "Retract this section",
                    );
                    retractBtn.addEventListener("click", () => {
                        det.open = false;
                        summary.scrollIntoView({ behavior: "smooth" });
                    });
                    footer.appendChild(retractBtn);
                    contentDiv.appendChild(footer);
                }
                history.replaceState(
                    { hash: section.id },
                    "",
                    `#${section.id}`,
                );
            }
        });
        parentElem.appendChild(details);
    });
}

function expandAndJumpToSection(sectionId) {
    const target = document.getElementById(sectionId);
    if (target && target.tagName === "SUMMARY") {
        let current = target.parentElement;
        while (current && current.tagName === "DETAILS") {
            if (current != target.parentElement) {
                // ensure the target will be the last set history
                current.open = true;
            }
            let next = current.parentElement;
            while (next && next.tagName !== "DETAILS") {
                next = next.parentElement;
            }
            current = next;
        }
        target.parentElement.open = true;
        target.scrollIntoView({ alignToTop: true });
    }
}

function handleInitialHash() {
    const sectionId = location.hash.slice(1);
    if (sectionId) {
        expandAndJumpToSection(sectionId);
    }
}

document.getElementById("toggle-view").addEventListener("click", () => {
    isFullView = !isFullView;
    const toc = document.getElementById("toc");
    const fullView = document.getElementById("full-view");
    const toggleBtn = document.getElementById("toggle-view");
    if (isFullView) {
        toc.style.display = "none";
        fullView.style.display = "block";
        if (!document.getElementById("full-content").innerHTML) {
            document.getElementById("full-content").innerHTML =
                marked.parse(fullMd);
        }
        toggleBtn.textContent = "View TOC";
    } else {
        toc.style.display = "block";
        fullView.style.display = "none";
        toggleBtn.textContent = "View Full HTML";
    }
    if (isSearching) {
        handleSearch(document.getElementById("content-search").value);
    }
});

const searchInput = document.getElementById("content-search");
let searchTimeout;
searchInput.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => handleSearch(e.target.value.trim()), 300);
});

searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        clearTimeout(searchTimeout);
        isEnterSearch = true;
        handleSearch(e.target.value.trim());
    }
});

function handleSearch(query) {
    const resultsSection = document.getElementById("search-results");
    const toc = document.getElementById("toc");
    const fullView = document.getElementById("full-view");
    if (query) {
        isSearching = true;
        const titleResults = fuseTitles.search(query);
        const lowerQuery = query.toLowerCase();
        const terms = lowerQuery.split(/\s+/).filter((t) => t.length > 0);
        const contentMatches = flatSections.filter((s) => {
            if (terms.length === 0) return false;
            const lc = s.content.toLowerCase();
            return terms.some((t) => lc.includes(t));
        });
        const contentResults = contentMatches.map((s) => ({
            item: s,
            score: 0.6,
        }));
        let allResults = [...titleResults, ...contentResults];
        const seen = new Set();
        allResults = allResults.filter((r) => {
            const id = r.item.id;
            if (seen.has(id)) return false;
            seen.add(id);
            return true;
        });
        allResults.sort((a, b) => a.score - b.score);
        renderSearchResults(
            allResults,
            document.getElementById("results-list"),
        );
        resultsSection.style.display = "block";
        toc.style.display = "none";
        fullView.style.display = "none";
        let hist_url = `?file=${encodeURIComponent(currentPath)}&q=${encodeURIComponent(query)}${location.hash}`;
        if (isEnterSearch) {
            history.pushState({ search: query }, "", hist_url);
        } else {
            history.replaceState({ search: query }, "", hist_url);
        }
        isEnterSearch = false;
    } else {
        isSearching = false;
        resultsSection.style.display = "none";
        if (isFullView) {
            fullView.style.display = "block";
        } else {
            toc.style.display = "block";
        }
        history.replaceState(
            { search: "" },
            "",
            `?file=${encodeURIComponent(currentPath)}${location.hash}`,
        );
    }
}

function renderSearchResults(results, container) {
    container.innerHTML = "";
    if (results.length === 0) {
        container.innerHTML = "<p>No results found</p>";
        return;
    }
    results.forEach((result) => {
        const section = result.item;
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = section.title;

        const jumpBtn = document.createElement("a");
        jumpBtn.innerHTML =
            '<i class="fas fa-external-link-alt"></i> Jump to Section';
        jumpBtn.className = "jump-btn";
        jumpBtn.href = `?file=${encodeURIComponent(currentPath)}#${section.id}`;
        jumpBtn.addEventListener("click", (e) => {
            e.preventDefault();
            isSearching = false;
            isFullView = false;
            document.getElementById("toc").style.display = "block";
            document.getElementById("full-view").style.display = "none";
            document.getElementById("search-results").style.display = "none";
            document.getElementById("toggle-view").textContent =
                "View Full HTML";
            let hist_url = `?file=${encodeURIComponent(currentPath)}#${section.id}`;
            history.pushState({ hash: section.id }, "", hist_url);
            expandAndJumpToSection(section.id);
        });
        summary.appendChild(jumpBtn);

        details.appendChild(summary);
        const contentDiv = document.createElement("div");
        contentDiv.className = "markdown-body";
        contentDiv.innerHTML = marked.parse(section.content || "");
        details.appendChild(contentDiv);
        container.appendChild(details);
    });
}

init();
