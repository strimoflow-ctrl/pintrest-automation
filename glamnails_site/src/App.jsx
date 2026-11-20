import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Search, Sparkles, Image as ImageIcon, ArrowLeft, X, ExternalLink, Heart, Download } from 'lucide-react';
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

  // Routing state based on window.location.hash
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
      {/* Top Glassmorphic Navbar */}
      <nav className="nav-bar">
        <div className="brand-title" onClick={goHome}>
          <span>💅</span> GLAM<span style={{ color: 'var(--rose-gold)' }}>NAILS</span>
        </div>
        <a 
          href={MONETAG_DIRECT_LINK} 
          target="_blank" 
          rel="noopener noreferrer"
          className="tag-pill active" 
          style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <Sparkles size={14} /> 2026 Lookbook
        </a>
      </nav>

      <main className="container animate-fade">
        {selectedCollection ? (
          /* ================= DETAIL LOOKBOOK VIEW ================= */
          <div className="detail-header">
            <button className="back-btn" onClick={goHome}>
              <ArrowLeft size={16} /> All Collections
            </button>

            <span className="tag-pill" style={{ display: 'inline-block', marginBottom: '0.75rem' }}>
              ✨ {selectedCollection.source_site} Collection
            </span>

            <h1 className="detail-title">{selectedCollection.title}</h1>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginBottom: '1.5rem' }}>
              📸 Showing {selectedCollection.image_count} Salon-Grade HD Nail Art Photos • Tap any photo to zoom in
            </p>

            {/* Featured Hero Image */}
            <div className="gallery-photo-card" style={{ maxHeight: '600px', cursor: 'pointer' }} onClick={() => setActiveModalImg(selectedCollection.featured_image)}>
              <img src={selectedCollection.featured_image} alt={selectedCollection.title} loading="eager" />
            </div>

            {/* MONETAG HIGH-RPM DIRECT LINK BUTTON 1 */}
            <div className="monetag-cta-card">
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '0.4rem' }}>
                🎨 View Exact Gel Polish Shades & Kit
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
                Click below to unlock the exact color codes, builder gels, and brushes used for this look:
              </p>
              <a href={MONETAG_DIRECT_LINK} target="_blank" rel="noopener noreferrer" className="cta-btn-main">
                ✨ Unlock Nail Shades & Polish List ➔
              </a>
            </div>

            {/* Full HD Gallery Grid of all images in collection */}
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: '2.5rem 0 1rem 0', color: 'var(--rose-gold)' }}>
              📸 All {selectedCollection.image_count} Design Angles & Variations
            </h2>

            <div className="detail-gallery">
              {selectedCollection.images.map((imgUrl, idx) => (
                <div 
                  key={idx} 
                  className="gallery-photo-card"
                  onClick={() => setActiveModalImg(imgUrl)}
                >
                  <img src={imgUrl} alt={`Design variation #${idx + 1}`} loading="lazy" />
                  <div style={{ position: 'absolute', bottom: '0.5rem', left: '0.5rem', background: 'rgba(0,0,0,0.7)', padding: '0.2rem 0.6rem', borderRadius: '999px', fontSize: '0.7rem', fontWeight: 700 }}>
                    #{idx + 1}
                  </div>
                </div>
              ))}
            </div>

            {/* MONETAG HIGH-RPM DIRECT LINK BUTTON 2 */}
            <div className="monetag-cta-card" style={{ marginTop: '3.5rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: '0.4rem' }}>
                📥 Download Full 2026 Nail Lookbook (PDF)
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
                Get the printable high-res nail design inspiration booklet directly to your phone:
              </p>
              <a href={MONETAG_DIRECT_LINK} target="_blank" rel="noopener noreferrer" className="cta-btn-main">
                💅 Download Free Nail Lookbook ➔
              </a>
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

      {/* Floating Sticky Mobile Ad Bar (100% Mobile Guarantee) */}
      <div className="sticky-mobile-bar">
        <a 
          href={MONETAG_DIRECT_LINK} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="sticky-cta-btn"
        >
          💅 Unlock 2026 Gel Shades & Polish Kit (Free) ➔
        </a>
      </div>

      {/* Fullscreen Image Lightbox Modal */}
      {activeModalImg && (
        <div className="modal-backdrop" onClick={() => setActiveModalImg(null)}>
          <div className="modal-img-wrap" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setActiveModalImg(null)}>
              <X size={28} />
            </button>
            <img src={activeModalImg} alt="Zoomed nail design" className="modal-img" />
            <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
              <a 
                href={MONETAG_DIRECT_LINK} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="cta-btn-main" 
                style={{ padding: '0.6rem 1.5rem', fontSize: '0.85rem' }}
              >
                ✨ View Exact Polish Shade for this Look ➔
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
