function onScanSuccess(decodedText, decodedResult) {
    const resultElement = document.getElementById('read-result');
    resultElement.innerText = decodedText;

    fetch(`/buscar_caja?codigo=${encodeURIComponent(decodedText)}`)
        .then(response => {
            if (response.status === 404) {
                resultElement.innerText = "❌ Caja no encontrada";
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.redirect_url) {
                resultElement.innerText = "📦 Caja encontrada, redirigiendo...";
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            }
        })
        .catch(error => {
            console.error("Error al buscar la caja:", error);
            resultElement.innerText = "⚠️ Error al buscar la caja";
        });
}

let html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", {
    fps: 10,
    qrbox: 250
});
html5QrcodeScanner.render(onScanSuccess);
