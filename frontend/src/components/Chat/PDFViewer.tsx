import { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import {
    X,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    RotateCw,
    Download,
    Loader2,
} from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configuration du worker PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.js',
    import.meta.url
  ).toString();

interface PDFViewerProps {
    url: string;
    initialPage?: number;
    onClose: () => void;
}

export default function PDFViewer({ url, initialPage = 1, onClose }: PDFViewerProps) {
    const [numPages, setNumPages] = useState<number>(0);
    const [currentPage, setCurrentPage] = useState(initialPage);
    const [scale, setScale] = useState(1.0);
    const [rotation, setRotation] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        setIsLoading(false);
        setError(null);
  }, []);

  const onDocumentLoadError = useCallback((err: Error) => {
        setError(`Erreur de chargement: ${err.message}`);
        setIsLoading(false);
  }, []);

  const goToPrevPage = () => setCurrentPage((p) => Math.max(1, p - 1));
    const goToNextPage = () => setCurrentPage((p) => Math.min(numPages, p + 1));
    const zoomIn = () => setScale((s) => Math.min(3, s + 0.25));
    const zoomOut = () => setScale((s) => Math.max(0.5, s - 0.25));
    const rotate = () => setRotation((r) => (r + 90) % 360);

  const filename = url.split('/').pop() || 'document.pdf';

  return (
        <div className="flex flex-col h-full bg-gray-900">
          {/* Barre d'outils */}
              <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        {/* Navigation pages */}
                                <button
                                              onClick={goToPrevPage}
                                              disabled={currentPage <= 1}
                                              className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 text-gray-300 transition-colors"
                                            >
                                            <ChevronLeft size={18} />
                                </button>button>
                                <span className="text-gray-300 text-sm min-w-[80px] text-center">
                                  {isLoading ? '...' : `${currentPage} / ${numPages}`}
                                </span>span>
                                <button
                                              onClick={goToNextPage}
                                              disabled={currentPage >= numPages}
                                              className="p-1.5 rounded hover:bg-gray-700 disabled:opacity-30 text-gray-300 transition-colors"
                                            >
                                            <ChevronRight size={18} />
                                </button>button>
                      
                                <div className="w-px h-5 bg-gray-600 mx-1" />
                      
                        {/* Zoom */}
                                <button
                                              onClick={zoomOut}
                                              className="p-1.5 rounded hover:bg-gray-700 text-gray-300 transition-colors"
                                            >
                                            <ZoomOut size={18} />
                                </button>button>
                                <span className="text-gray-300 text-sm min-w-[50px] text-center">
                                  {Math.round(scale * 100)}%
                                </span>span>
                                <button
                                              onClick={zoomIn}
                                              className="p-1.5 rounded hover:bg-gray-700 text-gray-300 transition-colors"
                                            >
                                            <ZoomIn size={18} />
                                </button>button>
                      
                                <div className="w-px h-5 bg-gray-600 mx-1" />
                      
                        {/* Rotation */}
                                <button
                                              onClick={rotate}
                                              className="p-1.5 rounded hover:bg-gray-700 text-gray-300 transition-colors"
                                              title="Pivoter"
                                            >
                                            <RotateCw size={18} />
                                </button>button>
                      </div>div>
              
                      <div className="flex items-center gap-2">
                                <span className="text-gray-400 text-xs truncate max-w-[200px]">{filename}</span>span>
                                <a
                                              href={url}
                                              download={filename}
                                              className="p-1.5 rounded hover:bg-gray-700 text-gray-300 transition-colors"
                                              title="Telecharger"
                                            >
                                            <Download size={18} />
                                </a>a>
                                <button
                                              onClick={onClose}
                                              className="p-1.5 rounded hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
                                            >
                                            <X size={18} />
                                </button>button>
                      </div>div>
              </div>div>
        
          {/* Zone PDF */}
              <div className="flex-1 overflow-auto flex items-start justify-center p-4 bg-gray-950">
                {error ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                                <div className="w-16 h-16 rounded-full bg-red-900/30 flex items-center justify-center">
                                              <X size={32} className="text-red-400" />
                                </div>div>
                                <p className="text-red-400 text-sm">{error}</p>p>
                                <a
                                                href={url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-blue-400 hover:text-blue-300 text-sm underline"
                                              >
                                              Ouvrir dans un nouvel onglet
                                </a>a>
                    </div>div>
                  ) : (
                    <div className="relative">
                      {isLoading && (
                                    <div className="absolute inset-0 flex items-center justify-center z-10 bg-gray-950/80">
                                                    <Loader2 size={32} className="text-blue-400 animate-spin" />
                                    </div>div>
                                )}
                                <Document
                                                file={url}
                                                onLoadSuccess={onDocumentLoadSuccess}
                                                onLoadError={onDocumentLoadError}
                                                loading={
                                                                  <div className="flex items-center justify-center w-[600px] h-[800px]">
                                                                                    <Loader2 size={32} className="text-blue-400 animate-spin" />
                                                                  </div>div>
                                  }
                                            >
                                              <Page
                                                                pageNumber={currentPage}
                                                                scale={scale}
                                                                rotate={rotation}
                                                                renderTextLayer={true}
                                                                renderAnnotationLayer={true}
                                                                className="shadow-2xl"
                                                              />
                                </Document>Document>
                    </div>div>
                      )}
              </div>div>
        
          {/* Barre de navigation bas */}
          {!isLoading && !error && numPages > 1 && (
                  <div className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-800 border-t border-gray-700 flex-shrink-0">
                            <button
                                          onClick={goToPrevPage}
                                          disabled={currentPage <= 1}
                                          className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 text-gray-300 text-sm transition-colors"
                                        >
                                        Precedent
                            </button>button>
                            <div className="flex gap-1">
                              {Array.from({ length: Math.min(5, numPages) }, (_, i) => {
                                  let page: number;
                                  if (numPages <= 5) {
                                                    page = i + 1;
                                  } else if (currentPage <= 3) {
                                                    page = i + 1;
                                  } else if (currentPage >= numPages - 2) {
                                                    page = numPages - 4 + i;
                                  } else {
                                                    page = currentPage - 2 + i;
                                  }
                                  return (
                                                    <button
                                                                        key={page}
                                                                        onClick={() => setCurrentPage(page)}
                                                                        className={`w-8 h-8 rounded text-sm transition-colors ${
                                                                                              page === currentPage
                                                                                                ? 'bg-blue-600 text-white'
                                                                                                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                                                                        }`}
                                                                      >
                                                      {page}
                                                    </button>button>
                                                  );
                  })}
                            </div>div>
                            <button
                                          onClick={goToNextPage}
                                          disabled={currentPage >= numPages}
                                          className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 text-gray-300 text-sm transition-colors"
                                        >
                                        Suivant
                            </button>button>
                  </div>div>
              )}
        </div>div>
      );
}</div>
