// App.js
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
    const [numLinks, setNumLinks] = useState(1);
    const [links, setLinks] = useState(Array(numLinks).fill(''));
    const [format, setFormat] = useState('mp3');
    const [loading, setLoading] = useState(false);
    const [showNotification, setShowNotification] = useState(false);

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
            setShowNotification(true);
            setTimeout(() => setShowNotification(false), 3000);
        } catch (error) {
            console.error('Error downloading files:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-container">
            <div className="app-container">
                <div className="glass-morphism">
                    <h1>YouTube Converter</h1>
                    <p className="subtitle">Convert your favorite videos to MP3 or MP4</p>
                    
                    <div className="input-group">
                        <label className="floating-label">
                            Number of Links
                            <input
                                type="number"
                                value={numLinks}
                                onChange={handleNumLinksChange}
                                min="1"
                                className="modern-input"
                            />
                        </label>
                    </div>

                    <div className="links-container custom-scrollbar">
                        {links.map((link, index) => (
                            <div key={index} className="input-group">
                                <label className="floating-label">
                                    YouTube Link {index + 1}
                                    <input
                                        type="text"
                                        value={link}
                                        onChange={(e) => handleLinkChange(index, e.target.value)}
                                        placeholder="https://youtube.com/..."
                                        className="modern-input"
                                    />
                                </label>
                            </div>
                        ))}
                    </div>

                    <div className="format-selector">
                        <label className="format-label">Output Format:</label>
                        <div className="format-options">
                            <button
                                className={`format-button ${format === 'mp3' ? 'active' : ''}`}
                                onClick={() => setFormat('mp3')}
                            >
                                MP3
                            </button>
                            <button
                                className={`format-button ${format === 'mp4' ? 'active' : ''}`}
                                onClick={() => setFormat('mp4')}
                            >
                                MP4
                            </button>
                        </div>
                    </div>

                    <button 
                        className={`submit-button ${loading ? 'loading' : ''}`}
                        onClick={handleSubmit} 
                        disabled={loading}
                    >
                        <span className="button-text">
                            {loading ? 'Converting...' : 'Start Converting'}
                        </span>
                        <span className="button-loader"></span>
                    </button>

                    {showNotification && (
                        <div className="notification">
                            Download completed successfully!
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;