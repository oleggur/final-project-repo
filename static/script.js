
document.addEventListener('DOMContentLoaded', function () {
    const field = document.getElementById('addCatField');
    const button = document.getElementById('addCatButton');
    field.onkeyup = function() {
        if (field.value.trim().length === 0) {
            button.disabled = true;
        } else {
            button.disabled = false;
        }
    }
});