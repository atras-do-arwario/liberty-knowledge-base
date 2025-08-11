// index.js
const repo = "atras-do-arwario/liberty-knowledge-base";
const branch = "main";

let files = [];
let fuse;

async function loadFiles() {
    try {
        const response = await fetch("files.json");
        if (!response.ok)
            throw new Error(`Failed to fetch files.json: ${response.status}`);
        files = await response.json();
        if (!Array.isArray(files))
            throw new Error("files.json is not an array");
        fuse = new Fuse(files, {
            includeScore: true,
            threshold: 0.6,
            ignoreLocation: true,
        });
        displayFiles(files);
    } catch (error) {
        console.error("Error loading files:", error);
        document.getElementById("file-list").innerHTML =
            "<li>Error loading files</li>";
    }
}

function displayFiles(fileList) {
    const ul = document.getElementById("file-list");
    ul.innerHTML = "";
    if (fileList.length === 0) {
        ul.innerHTML = "<li>No files found</li>";
        return;
    }
    fileList.forEach((file) => {
        const li = document.createElement("li");
        const filePath = typeof file === "string" ? file : file.item;
        li.textContent = filePath;
        li.setAttribute("role", "button");
        li.setAttribute("tabindex", "0");
        li.addEventListener("click", () => {
            window.location.href = `viewer.html?file=${encodeURIComponent(filePath)}`;
        });
        li.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                window.location.href = `viewer.html?file=${encodeURIComponent(filePath)}`;
            }
        });
        ul.appendChild(li);
    });
}

document.getElementById("search").addEventListener("input", (e) => {
    const query = e.target.value.trim();
    if (!query) {
        displayFiles(files);
        return;
    }
    const result = fuse.search(query);
    displayFiles(result);
});

loadFiles();
