import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
    const [numLinks, setNumLinks] = useState(1);
    const [links, setLinks] = useState(Array(numLinks).fill(''));
    const [format, setFormat] = useState('mp3');
    const [loading, setLoading] = useState(false);

    const handleLinkChange = (index, value) => {
        const newLinks = [...links];
        newLinks[index] = value;
        setLinks(newLinks);
    };

    const handleNumLinksChange = (e) => {
        const value = e.target.value;
        const newNumLinks = Math.max(1, parseInt(value) || 1);
        setNumLinks(newNumLinks);
        setLinks(Array(newNumLinks).fill(''));
    };

    const handleSubmit = async () => {
        setLoading(true);
        try {
            const response = await axios.post('http://localhost:5000/download', { links, format }, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'download.zip');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Error downloading files:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="App">
            <h1>YouTube to MP3/MP4 Converter</h1>
            <div className="input-container">
                <label>Number of Links:</label>
                <input
                    type="number"
                    value={numLinks}
                    onChange={handleNumLinksChange}
                    min="1"
                />
            </div>
            <div className="links-container">
                {links.map((link, index) => (
                    <div key={index} className="input-container">
                        <label>YouTube Link {index + 1}:</label>
                        <input
                            type="text"
                            value={link}
                            onChange={(e) => handleLinkChange(index, e.target.value)}
                            placeholder="Paste YouTube link here"
                        />
                    </div>
                ))}
            </div>
            <div className="input-container">
                <label>Output Format:</label>
                <select value={format} onChange={(e) => setFormat(e.target.value)}>
                    <option value="mp3">MP3</option>
                    <option value="mp4">MP4</option>
                </select>
            </div>
            <button onClick={handleSubmit} disabled={loading}>
                {loading ? 'Processing...' : 'Download'}
            </button>
        </div>
    );
}

export default App;