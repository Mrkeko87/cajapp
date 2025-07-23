function onScanSuccess(decodedText, decodedResult) {
  document.getElementById('read-result').innerText = decodedText;
  // Aquí puedes hacer una llamada fetch para obtener detalles si quieres:
  // fetch(`/api/objeto/${decodedText}`).then(res => res.json()).then(data => console.log(data));
}

function onScanError(errorMessage) {
  // Puedes manejar errores aquí si quieres
}

let html5QrcodeScanner = new Html5QrcodeScanner(
  "qr-reader", { fps: 10, qrbox: 250 });
html5QrcodeScanner.render(onScanSuccess, onScanError);
