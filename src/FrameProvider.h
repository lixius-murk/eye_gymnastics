#ifndef FRAMEPROVIDER_H
#define FRAMEPROVIDER_H

#include <QQuickImageProvider>
#include <QImage>
#include <QMutex>

#ifdef Q_OS_WIN
#include <windows.h>
#else
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#endif

static constexpr int HEADER_SIZE = 13; // 4 counter + 1 flag + 4 width + 4 height
static constexpr int MAX_W = 3840;
static constexpr int MAX_H = 2160;
static constexpr int BUF_SIZE = MAX_W * MAX_H * 3 + HEADER_SIZE;

class FrameProvider : public QQuickImageProvider
{
public:

    explicit FrameProvider()
        : QQuickImageProvider(QQuickImageProvider::Image)
    {}

    ~FrameProvider() { detach(); }

    QImage requestImage(const QString &, QSize *size, const QSize &) override
    {
        QMutexLocker lock(&m_mutex);
        if (!ensureAttached()) return blackFrame(size);

        const uchar *data = static_cast<const uchar *>(m_data);

        //if (data[4]) return blackFrame(size);

        quint32 w, h;
        memcpy(&w, data + 5, 4);
        memcpy(&h, data + 9, 4);

        if (w == 0 || h == 0 || w > MAX_W || h > MAX_H)
            return blackFrame(size);

        QImage img(data + HEADER_SIZE, w, h, w * 3, QImage::Format_RGB888);
        QImage copy = img.copy();
        if (size) *size = copy.size();
        return copy;
    }



private:
    void        *m_data = nullptr;
    QMutex       m_mutex;

#ifdef Q_OS_WIN
    HANDLE m_hFile   = INVALID_HANDLE_VALUE;
    HANDLE m_hMap    = nullptr;

    void detach()
    {
        if (m_data)  { UnmapViewOfFile(m_data); m_data = nullptr; }
        if (m_hMap)  { CloseHandle(m_hMap);     m_hMap = nullptr; }
        if (m_hFile != INVALID_HANDLE_VALUE) {
            CloseHandle(m_hFile);
            m_hFile = INVALID_HANDLE_VALUE;
        }
    }

    bool ensureAttached()
    {
        if (m_data) return true;

        m_hMap = OpenFileMappingA(FILE_MAP_READ, FALSE, "Global\\frames");
        if (!m_hMap) return false;

        m_data = MapViewOfFile(m_hMap, FILE_MAP_READ, 0, 0, BUF_SIZE);
        if (!m_data) { CloseHandle(m_hMap); m_hMap = nullptr; return false; }

        return true;
    }

#else
    int  m_fd    = -1;
    ino_t m_inode = 0;

    void detach()
    {
        if (m_data && m_data != MAP_FAILED) {
            munmap(m_data, BUF_SIZE);
            m_data = nullptr;
        }
        if (m_fd >= 0) { close(m_fd); m_fd = -1; }
        m_inode = 0;
    }

    bool ensureAttached()
    {
        if (m_data) {
            struct stat st;
            if (fstat(m_fd, &st) != 0 || st.st_nlink == 0)
                detach();
        }
        if (m_data) return true;

        int fd = open("/dev/shm/frames", O_RDONLY);
        if (fd < 0) return false;

        void *map = mmap(nullptr, BUF_SIZE, PROT_READ, MAP_SHARED, fd, 0);
        if (map == MAP_FAILED) { close(fd); return false; }

        struct stat st;
        fstat(fd, &st);
        m_fd    = fd;
        m_data  = map;
        m_inode = st.st_ino;
        return true;
    }
#endif

    QImage blackFrame(QSize *size)
    {
        QImage img(640, 480, QImage::Format_RGB888);
        img.fill(Qt::black);
        if (size) *size = img.size();
        return img;
    }
};

#endif // FRAMEPROVIDER_H
