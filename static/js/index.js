document.getElementById('search-button').addEventListener('click', () => {
    const url = document.getElementById('url-input').value;

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '';

        if (data.exists) {
            const productInfo = `
                <h2>${data.product.name}</h2>
                <img src="${data.product.image_url}" alt="Product Image" />
                <p>모델: ${data.product.model}</p>
                <p>옵션: ${data.product.options}</p>
                <h3>가격 히스토리</h3>
                <ul>
                    ${data.price_history.map(history => `<li>${history.date}: ${history.original_price}원 (임직원가: ${history.employee_price}원)</li>`).join('')}
                </ul>
            `;
            resultDiv.innerHTML = productInfo;
        } else {
            if (confirm(data.message)) {
                fetch('/collect_data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url }),
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                });
            }
        }
    });
});
