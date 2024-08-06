"use client";
import { useState } from 'react';
import Image from 'next/image';

export default function Home() {
  const [gpuType, setGpuType] = useState<string>('');
  const [tokenId, setTokenId] = useState<string>('');
  const [tokenSecret, setTokenSecret] = useState<string>('');
  const [isDeployed, setIsDeployed] = useState<boolean>(false);
  const [backendUrl, setBackUrl] = useState<string>('');
  const [prompt, setPrompt] = useState<string>('');
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);

  const handleDeploy = async () => {
    // call /api/deploy (post with json: {"token_id": "", "token_secret"})
    try {
      // Define the payload to be sent in the request
      const payload = {
        modal_token_id: tokenId, // Replace with actual token_id if needed
        modal_token_secret: tokenSecret, // Replace with actual token_secret if needed
      };

      // Make the POST request to /api/deploy
      const response = await fetch('/api/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      // Check if the response is okay (status code 200-299)
      if (response.ok) {
        const result = await response.json();
        console.log('Deployment successful:', result);
        // Optionally handle the successful response here
        setIsDeployed(true);
        setBackUrl(result.url)
      } else {
        // Handle errors or unsuccessful responses
        console.error('Deployment failed:', response.statusText);
      }
    } catch (error) {
      // Handle any network or other errors
      console.error('An error occurred:', error);
    }
  };

  const handleRun = async () => {
    try {
      // Send the request to generate an image
      const response = await fetch('/api/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt, backend_url: backendUrl }),
      });
      const data = await response.json();

      if (data.status === "processing") {
        const { task_id } = data;
        // Poll for task status
        console.log(`Task id: ${task_id}`)

        const checkStatus = async () => {
          const statusResponse = await fetch(`/api/task-status/${task_id}`);
          const statusData = await statusResponse.json();

          if (statusData.status === "completed") {
            const imageBase64 = statusData.image_base64;
            setGeneratedImage(`data:image/png;base64,${imageBase64}`);
          } else if (statusData.status === "failed") {
            console.error('Image generation failed:', statusData.message);
          } else {
            // Retry after a delay
            console.log("polling")
            setTimeout(checkStatus, 2000);
          }
        };
        checkStatus();
      }
    } catch (error) {
      console.error('Error generating image:', error);
    }
  };

  return (
    <div className="container mx-auto p-10 flex-col justify-center min-h-screen">
      <div className="flex flex-col items-center w-full">
        <h1 className="text-4xl font-bold mb-6 text-center">Fluxwell</h1>
      </div>
      <div className="w-full mx-auto max-w-4xl">
        {/* Align horizontal center */}
        <div className="flex flex-col items-center w-full">
          <div className="form-control w-full max-w-lg mb-4">
            <label className="label">
              <span className="label-text">GPU Type</span>
            </label>
            <select
              className="select select-bordered"
              value={gpuType}
              onChange={(e) => setGpuType(e.target.value)}
            >
              <option>T4</option>
              <option>A10G</option>
              <option>A100</option>
            </select>
          </div>

          <div className="form-control w-full max-w-lg mb-4">
            <label className="label">
              <span className="label-text">Token id</span>
            </label>
            <input
              type="text"
              placeholder="Enter token id"
              className="input input-bordered w-full max-w-lg"
              value={tokenId}
              onChange={(e) => setTokenId(e.target.value)}
            />
          </div>

          <div className="form-control w-full max-w-lg mb-4">
            <label className="label">
              <span className="label-text">Token secret</span>
            </label>

            <input
              type="text"
              placeholder="Enter token secret"
              className="input input-bordered w-full max-w-lg mb-4"
              value={tokenSecret}
              onChange={(e) => setTokenSecret(e.target.value)}
            />
          </div>

          <button
            className="btn btn-primary mb-4 max-w-xs"
            onClick={handleDeploy}
          >
            Deploy Model
          </button>
        </div>
      </div>

      {isDeployed && (
        <div className="form-control w-full flex-col justify-center mb-4">
          <label className="label">
            <span className="label-text">Prompt</span>
          </label>
          <textarea
            className="textarea textarea-bordered h-24"
            placeholder="Enter your prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          ></textarea>
          <button
            className="btn btn-primary mt-2"
            onClick={handleRun}
          >
            Run
          </button>
        </div>
      )}

      {generatedImage && (
        <div className="mt-4">
          <h2 className="text-xl font-bold mb-2">Generated Image:</h2>
          <Image src={generatedImage} alt="Generated image" width={300} height={300} />
        </div>
      )}
    </div>
  );
}