// static/js/geolocation.js

function getUserLocationAndFetchWeather() {
  if (!navigator.geolocation) {
    console.error("Geolocation is not supported by your browser.");
    fetchWeatherFallback(); // Use IP-based backend fallback
    return;
  }

  navigator.geolocation.getCurrentPosition(
    // ✅ Success callback
    function (position) {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      console.log(`📍 Browser location: ${lat}, ${lon}`);

      // Call your Flask backend with lat/lon
      fetch(`/api/weather?lat=${lat}&lon=${lon}`)
        .then(response => response.json())
        .then(data => {
          console.log("🌦 Weather data:", data);
          displayWeather(data);
        })
        .catch(err => {
          console.error("Error fetching weather:", err);
        });
    },

    // ❌ Error callback
    function (error) {
      console.warn("Geolocation error:", error.message);
      fetchWeatherFallback(); // Fallback to IP-based location
    }
  );
}

function fetchWeatherFallback() {
  // Calls backend without lat/lon so backend uses IP lookup
  fetch(`/api/weather`)
    .then(response => response.json())
    .then(data => {
      console.log("🌦 Weather data (IP fallback):", data);
      displayWeather(data);
    })
    .catch(err => {
      console.error("Error fetching fallback weather:", err);
    });
}

function displayWeather(data) {
  const output = document.getElementById("weather-output");
  if (!output) return;

  if (data.error) {
    output.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
    return;
  }

  output.innerHTML = `
    <strong>Temp:</strong> ${data.temp}°C<br>
    <strong>Humidity:</strong> ${data.humidity}%<br>
    <strong>Pressure:</strong> ${data.pressure} hPa<br>
    <strong>Condition:</strong> ${data.description}
  `;
}

// Auto-run on page load
document.addEventListener("DOMContentLoaded", getUserLocationAndFetchWeather);
