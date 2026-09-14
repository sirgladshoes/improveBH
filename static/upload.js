const folderInput = document.getElementById("replayFolder");
const uploadButton = document.getElementById("uploadButton");
const status = document.getElementById("status");

uploadButton.addEventListener("click", async () => {

    const files = folderInput.files;

    if (files.length === 0) {
        status.textContent = "Please select your replay folder.";
        return;
    }

    status.textContent = "Creating ZIP...";

    const zip = new JSZip();

    let replayCount = 0;

    const replayFiles = [];

    for (const file of files) {
        if (file.name.endsWith(".replay")) {
            replayFiles.push(file);
        }
    }

    replayFiles.sort((a, b) => b.lastModified - a.lastModified);

    const selectedFiles = replayFiles.slice(0, 100000);

    for (const file of selectedFiles) {
        console.log(file.name, new Date(file.lastModified));

        zip.file(file.webkitRelativePath, file, {
            date: new Date(file.lastModified)
        });

        replayCount++;
    }



    console.log("replayCount:", replayCount);
    console.log("zip files:", Object.keys(zip.files).length);

    status.textContent = `Found ${replayCount} replays. Creating ZIP...`;

    const zipBlob = await zip.generateAsync({
        type: "blob"
    });

    status.textContent = "Uploading...";

    const formData = new FormData();

    formData.append("file", zipBlob, "replays.zip");

    const response = await fetch("/upload", {
        method: "POST",
        body: formData
    });

    if (response.ok) {
        status.textContent = "Upload complete!";
    } else {
        status.textContent = "Upload failed.";
    }
});