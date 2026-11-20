import React, { useState, useEffect, useMemo } from 'react';
import { Search, Sparkles, Image as ImageIcon, ArrowLeft, X, Download } from 'lucide-react';
import rawData from './data/collections.json';

const MONETAG_DIRECT_LINK = "https://uplcm.com/4/12271752";

const TAG_FILTERS = [
  "All Looks",
  "Almond",
  "French Tips",
  "Coffin",
  "Chrome",
  "Velvet",
  "3D Nails",
  "Fall & Winter",
  "Minimalist"
];

export default function App() {
  const collections = rawData.collections || [];

  // Routing state based on window.location.hash and pathname
  const [currentHash, setCurrentHash] = useState(window.location.hash || '');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState('All Looks');
  const [visibleCount, setVisibleCount] = useState(16);
  const [activeModalImg, setActiveModalImg] = useState(null);

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentHash(window.location.hash);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Determine current route: /nail/:slug or #/nail/:slug
  const activeSlug = useMemo(() => {
    const pathname = window.location.pathname;
    const pathMatch = pathname.match(/\/(?:nail|lookbook)\/([^/?#]+)/);
    if (pathMatch) return pathMatch[1];

    if (currentHash) {
      const hashMatch = currentHash.match(/#\/(?:nail|lookbook)\/([^/?#]+)/);
      if (hashMatch) return hashMatch[1];
    }
    return null;
  }, [currentHash]);

  const selectedCollection = useMemo(() => {
    if (!activeSlug) return null;
    return collections.find(c => c.slug === activeSlug) || null;
  }, [activeSlug, collections]);

  // Navigate helper
  const navigateTo = (slug) => {
    window.location.hash = `#/nail/${slug}`;
  };

  const goHome = () => {
    window.location.hash = '';
  };

  // Download handler: Opens Monetag Direct Link in new tab AND triggers real image file download
  const handleDownload = (e, imgUrl, title, index = 1) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }

    // 1. Open Monetag Ad link in a new tab
    window.open(MONETAG_DIRECT_LINK, '_blank', 'noopener,noreferrer');

    // 2. Trigger real image download
    try {
      fetch(imgUrl)
        .then(res => res.blob())
        .then(blob => {
          const blobUrl = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = blobUrl;
          const safeTitle = (title || 'nail-design').toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 30);
          a.download = `${safeTitle}-${index}.jpg`;
          document.body.appendChild(a);
          a.click();
          setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(blobUrl);
          }, 200);
        })
        .catch(() => {
          // Fallback if cross-origin fetch is restricted
          const a = document.createElement('a');
          a.href = imgUrl;
          a.target = '_blank';
          a.download = `nail-design-${index}.jpg`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        });
    } catch (err) {
      console.log('Download trigger:', err);
    }
  };

  // Filter collections
  const filteredCollections = useMemo(() => {
    return collections.filter(c => {
      const titleLower = c.title.toLowerCase();
      const slugLower = c.slug.toLowerCase();

      // Tag filter
      if (selectedTag !== "All Looks") {
        const tagK = selectedTag.toLowerCase().replace("&", "").trim();
        const matchesTag = titleLower.includes(tagK) || slugLower.includes(tagK);
        if (!matchesTag) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        return titleLower.includes(q) || slugLower.includes(q);
      }

      return true;
    });
  }, [collections, selectedTag, searchQuery]);

  // Infinite Scroll / Lazy Buffering: load next batch when user scrolls near bottom
  useEffect(() => {
    const handleScroll = () => {
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 600) {
        setVisibleCount(prev => Math.min(prev + 12, filteredCollections.length));
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [filteredCollections.length]);

  return (
    <div>
      {/* Top Glassmorphic Navbar (Clean & Minimal) */}
      <nav className="nav-bar">
        <div className="brand-title" onClick={goHome}>
          <span>💅</span> GLAM<span style={{ color: 'var(--rose-gold)' }}>NAILS</span>
        </div>
      </nav>

      <main className="container animate-fade">
        {selectedCollection ? (
          /* ================= DETAIL LOOKBOOK VIEW ================= */
          <div className="detail-header">
            <div style={{ marginBottom: '1rem' }}>
              <button className="back-btn" onClick={goHome}>
                <ArrowLeft size={16} /> All Collections
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
              <span className="tag-pill" style={{ padding: '0.2rem 0.65rem', fontSize: '0.72rem' }}>
                ✨ {selectedCollection.source_site} Collection
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                {selectedCollection.image_count} HD Photos
              </span>
            </div>

            <h1 className="detail-title">{selectedCollection.title}</h1>

            {/* Featured Hero Image with subtle download icon */}
            <div 
              className="gallery-photo-card hero-card"
              onClick={() => setActiveModalImg(selectedCollection.featured_image)}
            >
              <img src={selectedCollection.featured_image} alt={selectedCollection.title} loading="eager" />
              <button 
                type="button"
                className="img-download-icon" 
                onClick={(e) => handleDownload(e, selectedCollection.featured_image, selectedCollection.title, 1)}
                title="Download HD photo"
              >
                <Download size={16} />
              </button>
            </div>

            {/* Full HD Gallery Grid */}
            <div style={{ margin: '2rem 0 1rem 0' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--rose-gold)' }}>
                📸 All {selectedCollection.image_count} Design Angles
              </h2>
            </div>

            <div className="detail-gallery">
              {selectedCollection.images.map((imgUrl, idx) => (
                <div 
                  key={idx} 
                  className="gallery-photo-card"
                  onClick={() => setActiveModalImg(imgUrl)}
                >
                  <img src={imgUrl} alt={`Design variation #${idx + 1}`} loading="lazy" />
                  
                  {/* Subtle clean download icon on each image */}
                  <button 
                    type="button"
                    className="img-download-icon"
                    onClick={(e) => handleDownload(e, imgUrl, selectedCollection.title, idx + 1)}
                    title="Download HD photo"
                  >
                    <Download size={14} />
                  </button>

                  <div className="photo-idx-badge">
                    #{idx + 1}
                  </div>
                </div>
              ))}
            </div>

          </div>
        ) : (
          /* ================= HOME FEED LOOKBOOKS VIEW ================= */
          <div>
            {/* Search and Tag Filters */}
            <div className="filter-section">
              <div className="search-box">
                <Search size={18} className="search-icon" />
                <input
                  type="text"
                  placeholder="Search 480+ nail collections (e.g. Almond, French, Chrome)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input"
                />
              </div>

              {/* Tag scroll */}
              <div className="tags-scroll">
                {TAG_FILTERS.map(tag => (
                  <button
                    key={tag}
                    onClick={() => { setSelectedTag(tag); setVisibleCount(16); }}
                    className={`tag-pill ${selectedTag === tag ? 'active' : ''}`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Count indicator */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <span>Showing <strong>{filteredCollections.length}</strong> Genuine Lookbooks</span>
              <span>✨ 9,950+ HD Photos</span>
            </div>

            {/* Cards Grid with Lazy Load */}
            <div className="cards-grid">
              {filteredCollections.slice(0, visibleCount).map((col) => (
                <div 
                  key={col.id} 
                  className="nail-card"
                  onClick={() => navigateTo(col.slug)}
                >
                  <div className="card-img-wrap">
                    <img src={col.featured_image} alt={col.title} className="card-img" loading="lazy" />
                    <div className="card-badge">
                      <ImageIcon size={12} /> {col.image_count} Photos
                    </div>
                  </div>
                  <div className="card-content">
                    <h3 className="card-title">{col.title}</h3>
                    <div className="card-footer">
                      <span>✨ {col.source_site}</span>
                      <span style={{ color: 'var(--rose-gold)', fontWeight: 600 }}>View Lookbook ➔</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Infinite Scroll Trigger Loader */}
            {visibleCount < filteredCollections.length && (
              <div style={{ textAlign: 'center', margin: '2.5rem 0' }}>
                <button 
                  onClick={() => setVisibleCount(prev => prev + 16)} 
                  className="tag-pill" 
                  style={{ padding: '0.75rem 2rem', fontSize: '0.9rem', cursor: 'pointer' }}
                >
                  ⏳ Loading more beautiful nail sets...
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Fullscreen Image Lightbox Modal */}
      {activeModalImg && (
        <div className="modal-backdrop" onClick={() => setActiveModalImg(null)}>
          <div className="modal-img-wrap" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setActiveModalImg(null)}>
              <X size={26} />
            </button>
            <img src={activeModalImg} alt="Zoomed nail design" className="modal-img" />
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <button 
                type="button"
                className="action-download-pill" 
                style={{ padding: '0.65rem 1.5rem', fontSize: '0.9rem', display: 'inline-flex', border: 'none', cursor: 'pointer' }}
                onClick={(e) => handleDownload(e, activeModalImg, selectedCollection?.title, 1)}
              >
                <Download size={15} /> Save HD Photo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
