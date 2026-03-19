let selectedCourse = null;

function openDeleteModal(subject, catalog, termid) {
    selectedCourse = { subject, catalog, termid };

    document.getElementById("deleteText").innerText =
        `Delete ${subject} ${catalog} from this semester?`;

    document.getElementById("deleteModal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("deleteModal").classList.add("hidden");
}

function confirmDelete() {
    fetch("/delete-course", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(selectedCourse)
    })
    .then(() => location.reload())
    .catch(err => console.error(err));
}