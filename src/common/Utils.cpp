#include "Utils.h"

namespace Utils
{
    QStringList splitCsv(const QString &line)
    {
        // Simple CSV split (no quoted fields)
        return line.split(",");
    }
}
