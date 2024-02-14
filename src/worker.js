addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
});

const subscriptionLinks = [
  "https://raw.githubusercontent.com/mshojaei77/v2rayAuto/main/auto#Shojaei2ray",
];

async function handleRequest(request) {
  try {
    // Fetch all subscription links and flatten the arrays
    const configLinksArrays = await Promise.all(subscriptionLinks.map(link => extractV2rayConfigs(link)));
    const allLinks = configLinksArrays.flat();
    
    // Remove duplicates using Set and convert back to an array
    const uniqueLinks = [...new Set(allLinks)];
    
    // Create the response header with the total number of unique configs
    const responseHeader = `# Total Configs: ${uniqueLinks.length}\n`;
    
    // Join the unique configs into a single string with line breaks
    const responseBody = responseHeader + uniqueLinks.join('\n');
    
    // Return the response with the unique v2ray configs and header
    return new Response(responseBody, {
      status:  200,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'public, max-age=3600' // Cache for  1 hour
      }
    });
  } catch (error) {
    return new Response(`Failed to fetch configs: ${error.message}`, { status:  500 });
  }
}

async function extractV2rayConfigs(subscriptionLink) {
  try {
    const controller = new AbortController();
    const signal = controller.signal;
    setTimeout(() => controller.abort(),  15000); // Timeout after  15 seconds per link

    const response = await fetch(subscriptionLink, { signal });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    
    const text = await response.text();
    return text.split("\n").filter(Boolean); // Filter out empty lines
  } catch (error) {
    console.error(`Failed to fetch ${subscriptionLink}: ${error.message}`);
    throw error; // Re-throw the error to be caught by Promise.all
  }
}
