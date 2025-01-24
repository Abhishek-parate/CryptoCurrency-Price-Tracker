const socket = io();
const currencySelector = document.getElementById("currency-selector");
let selectedCurrency = "USD";

socket.on("price_update", (data) => {
  const { symbol, price, volume, change } = data;

  const upperSymbol = symbol.toUpperCase();
  const priceValue = document.getElementById(`price-value-${upperSymbol}`);
  const volumeValue = document.getElementById(`volume-value-${upperSymbol}`);
  const changeValue = document.getElementById(`change-value-${upperSymbol}`);

  if (priceValue && volumeValue && changeValue) {
    fetch(`/convert?amount=${price}&from=USD&to=${selectedCurrency}`)
      .then((response) => response.json())
      .then((converted) => {
        const existingPrice = parseFloat(
          priceValue.textContent.replace(/[^0-9.-]+/g, "")
        );
        const newPrice = converted.converted;

        priceValue.textContent = `${selectedCurrency} ${newPrice.toFixed(2)}`;
        volumeValue.textContent = `Volume: ${volume.toFixed(2)}`;
        changeValue.textContent = `Change: ${change.toFixed(2)}%`;

        if (existingPrice) {
          priceValue.classList.remove("text-green-500", "text-red-500");
          const changeClass =
            newPrice > existingPrice ? "text-green-500" : "text-red-500";
          priceValue.classList.add(changeClass);
        }
      });
  }
});

currencySelector.addEventListener("change", (e) => {
  selectedCurrency = e.target.value;
});


